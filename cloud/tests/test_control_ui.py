"""Exercise the served browser script against transport failures and setup data."""
from html.parser import HTMLParser
import json
import shutil
import subprocess
import unittest

from ninai_cloud.control_ui import render_control_center


class ControlUiTest(unittest.TestCase):
    def test_help_is_available_in_every_auth_state(self):
        for oauth, signed_in in ((True, False), (True, True), (False, False)):
            page = render_control_center(oauth_enabled=oauth, signed_in=signed_in)
            footer = page.split('<footer', 1)[1].split('</footer>', 1)[0]
            self.assertIn('Help and feedback', footer)
            self.assertIn('href="#setup-help"', page)
            self.assertIn('mailto:hello@ninai.io', footer)
            self.assertIn('Remove tokens, authorization codes', footer)
            self.assertNotIn(' hidden', footer)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed to exercise the browser script')
    def test_browser_errors_and_progressive_permissions(self):
        script = render_control_center(oauth_enabled=True).split('<script>', 1)[1].split('</script>', 1)[0]
        harness = r'''
const vm=require('node:vm'), assert=require('node:assert/strict');
let elements=new Map(), timers=[], cleared=[];
const element=selector=>{if(!elements.has(selector))elements.set(selector,{hidden:false,value:'',innerHTML:'',textContent:'',scrollIntoView(){}});return elements.get(selector)};
let context=vm.createContext({document:{querySelector:element},sessionStorage:{getItem(){return ''}},AbortController,setTimeout(fn){timers.push(fn);return timers.length},clearTimeout(id){cleared.push(id)},location:{origin:'https://app.example'},URL,Blob,console});
vm.runInContext(SCRIPT,context);
async function fails(fetch, expected){context.fetch=fetch;await assert.rejects(vm.runInContext("api('/overview')",context),e=>e.message.includes(expected));}
(async()=>{
await fails(async()=>({ok:false,status:502,json:async()=>{throw Error('HTML proxy error')}}),'HTTP 502');
await fails(async()=>{throw TypeError('Failed to fetch')},'Could not reach Ninai');
await fails(async()=>{let e=Error();e.name='AbortError';throw e},'took too long');
await fails(async()=>({ok:false,status:401,json:async()=>({})}),'session has expired');
assert.equal(cleared.length,4);
await vm.runInContext('downloadExport()',context);
assert.match(element('#notice').textContent,/session has expired/);
context.fetch=async url=>({ok:true,status:200,json:async()=>{
if(url.endsWith('/overview'))return {counts:{},workspace:{slug:'test'}};
if(url.endsWith('/capture-settings'))return {};
if(url.endsWith('/projects'))return {items:[{id:'p1',name:'Test'}]};
if(url.endsWith('/connections'))return {items:[{id:'c1',status:'active',display_name:'AI'}]};
return {items:[]};
}});
await vm.runInContext('load()',context);
let page=element('#app').innerHTML;
assert.match(page,/<details class="advanced"><summary>Choose project access<\/summary>/);
assert.match(page,/<summary>Sessions and capture<\/summary>/);
assert.match(page,/<summary>Recent disclosures<\/summary>/);
assert.match(page,/<option value="">Choose a project<\/option>/);
assert.match(page,/grant-propose-c1" type="checkbox">/);
process.stdout.write(page);
})().catch(e=>{console.error(e);process.exitCode=1});
'''.replace('SCRIPT', json.dumps(script))
        result = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        class DisclosureParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
            def handle_starttag(self, tag, attrs):
                if tag == 'details':
                    self.depth += 1
            def handle_endtag(self, tag):
                if tag == 'details':
                    self.depth -= 1
                    assert self.depth >= 0
        parser = DisclosureParser()
        parser.feed(result.stdout)
        self.assertEqual(parser.depth, 0)
