"use client";

import { useEffect, useRef, useState } from "react";

type Chapter = { id: string; title: string; start: number; end: number; instruction: string; success: string };
const progressKey = "ninai-install-walkthrough-completed-v1";

function timestamp(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export default function InstallWalkthrough() {
  const video = useRef<HTMLVideoElement>(null);
  const lastPause = useRef<string | null>(null);
  const pendingSeek = useRef<number | null>(null);
  const previousTime = useRef(0);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [completed, setCompleted] = useState<string[]>([]);
  const [current, setCurrent] = useState(0);
  const [pauseAfterStep, setPauseAfterStep] = useState(false);
  const [notice, setNotice] = useState("");
  const [transcript, setTranscript] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch("/assets/ninai-install-chapters.json")
      .then((response) => { if (!response.ok) throw new Error(); return response.json(); })
      .then((data) => {
        if (!Array.isArray(data.chapters) || !data.chapters.length) throw new Error();
        const valid = data.chapters.every((chapter: Chapter, index: number) =>
          chapter && typeof chapter.id === "string" && typeof chapter.title === "string" &&
          typeof chapter.instruction === "string" && typeof chapter.success === "string" &&
          Number.isFinite(chapter.start) && Number.isFinite(chapter.end) && chapter.start >= 0 && chapter.end > chapter.start &&
          (!index || chapter.start >= data.chapters[index - 1].end));
        if (!valid || new Set(data.chapters.map((chapter: Chapter) => chapter.id)).size !== data.chapters.length) throw new Error();
        if (!cancelled) setChapters(data.chapters);
      }).catch(() => { if (!cancelled) setNotice("Chapters are unavailable. You can still use the video controls and captions."); });
    fetch("/assets/ninai-install-guide.vtt")
      .then((response) => { if (!response.ok) throw new Error(); return response.text(); })
      .then((text) => {
        const cues = text.replace(/\r/g, "").split(/\n\s*\n/).flatMap((block) => {
          const lines = block.split("\n");
          const timing = lines.findIndex((line) => line.includes("-->"));
          return timing < 0 ? [] : [lines.slice(timing + 1).join(" ").replace(/<[^>]*>/g, "")];
        }).filter(Boolean);
        if (!cancelled) setTranscript(cues);
      }).catch(() => { /* The chapter text guide remains available. */ });
    try {
      const stored = JSON.parse(localStorage.getItem(progressKey) || "[]");
      if (Array.isArray(stored)) setCompleted(stored.filter((id) => typeof id === "string"));
    } catch { /* Watching the guide does not require browser storage. */ }
    return () => { cancelled = true; };
  }, []);

  const active = chapters[current];
  const completedCount = chapters.filter((chapter) => completed.includes(chapter.id)).length;

  function seek(index: number) {
    if (!video.current) return;
    video.current.pause();
    previousTime.current = chapters[index].start;
    if (video.current.readyState === 0) {
      pendingSeek.current = chapters[index].start;
      video.current.load();
    } else {
      video.current.currentTime = chapters[index].start;
    }
    setCurrent(index);
    lastPause.current = null;
    setNotice(`Step ${index + 1} selected. Press Play when you are ready.`);
  }

  function updateTime() {
    const player = video.current;
    if (!player || !chapters.length) return;
    const time = player.currentTime;
    const previous = previousTime.current;
    previousTime.current = time;
    const pausedChapter = chapters.find((chapter) => chapter.id === lastPause.current);
    if (player.paused && pausedChapter && time >= pausedChapter.end && time < pausedChapter.end + 0.7) {
      setCurrent(chapters.indexOf(pausedChapter));
      return;
    }
    const index = chapters.findIndex((chapter) => time >= chapter.start && time < chapter.end);
    if (index >= 0) setCurrent(index);
    const crossed = chapters.find((chapter) => previous < chapter.end && time >= chapter.end);
    if (pauseAfterStep && crossed && !player.paused && !player.seeking && lastPause.current !== crossed.id) {
      lastPause.current = crossed.id;
      player.pause();
      setCurrent(chapters.indexOf(crossed));
      setNotice(`Paused after ${crossed.title}. Try the step in Ninai, then press Play to continue.`);
    }
  }

  function markComplete(id: string) {
    const next = completed.includes(id) ? completed.filter((value) => value !== id) : [...completed, id];
    setCompleted(next);
    try { localStorage.setItem(progressKey, JSON.stringify(next)); } catch { /* Keep progress for this visit. */ }
  }

  return (
    <section className="setup-walkthrough shell" aria-labelledby="video-title">
      <div className="setup-walkthrough__heading">
        <div><p className="section-label">Watch, then try</p><h2 id="video-title">Follow a real setup walkthrough.</h2></div>
        <p>Recorded in Ninai with sample project data. Watch the actual screens, jump to a step, and check it off after you have tried it. This guide shows the product workflow; signed Mac installation is still pending.</p>
      </div>
      <div className="setup-walkthrough__grid">
        <div>
          <video ref={video} className="setup-walkthrough__video" controls playsInline preload="metadata" poster="/assets/ninai-install-poster.jpg" onTimeUpdate={updateTime} onLoadedMetadata={() => { if (video.current && pendingSeek.current !== null) { video.current.currentTime = pendingSeek.current; pendingSeek.current = null; } }} onError={() => setNotice("The video could not load. Use the text guide below, or download the recording to watch locally.")} aria-label="Ninai setup walkthrough with sample data">
            <source src="/assets/ninai-install-guide.mp4" type="video/mp4" />
            <track kind="captions" src="/assets/ninai-install-guide.vtt" srcLang="en" label="English" default />
            Your browser cannot play this video. Use the step-by-step text guide below.
          </video>
          <div className="setup-walkthrough__playback">
            <label><input type="checkbox" checked={pauseAfterStep} onChange={(event) => { setPauseAfterStep(event.target.checked); lastPause.current = null; }} /> Pause after each step so I can try it</label>
            <a href="/assets/ninai-install-guide.mp4" download>Download video</a>
          </div>
          {active && <div className="setup-walkthrough__instruction">
            <p className="section-label">Step {current + 1} of {chapters.length}</p>
            <h3>{active.title}</h3><p>{active.instruction}</p>
            <p><strong>You are done when:</strong> {active.success}</p>
            <button className="button button--ink" type="button" aria-pressed={completed.includes(active.id)} onClick={() => markComplete(active.id)}>{completed.includes(active.id) ? "✓ Step completed — undo" : "I tried this — mark complete"}</button>
          </div>}
          <p className="setup-walkthrough__notice" role="status">{notice}</p>
        </div>
        <nav className="setup-walkthrough__chapters" aria-label="Video chapters">
          <div className="setup-walkthrough__progress"><h3>Your setup checklist</h3><p>{completedCount} of {chapters.length} steps tried</p><progress max={Math.max(chapters.length, 1)} value={completedCount} aria-label="Steps you marked complete" /></div>
          <ol>{chapters.map((chapter, index) => <li key={chapter.id}><button type="button" className={current === index ? "is-active" : ""} aria-current={current === index ? "step" : undefined} onClick={() => seek(index)}><span className="setup-walkthrough__step" aria-label={completed.includes(chapter.id) ? "Completed" : `Step ${index + 1}`}>{completed.includes(chapter.id) ? "✓" : String(index + 1).padStart(2, "0")}</span><span>{chapter.title}<small>{timestamp(chapter.start)}</small></span></button></li>)}</ol>
          <p className="setup-walkthrough__storage">Checkmarks stay in this browser. They do not grant access or confirm that an assistant is connected.</p>
          <button className="setup-walkthrough__reset" type="button" disabled={!completed.length} onClick={() => { setCompleted([]); try { localStorage.removeItem(progressKey); } catch {} setNotice("Only this guide’s checkmarks were reset."); }}>Reset checklist</button>
        </nav>
      </div>
      {chapters.length > 0 && <details className="setup-walkthrough__transcript"><summary>Read the step-by-step text guide</summary><ol>{chapters.map((chapter) => <li key={chapter.id}><h3>{chapter.title}</h3><p>{chapter.instruction}</p><p><strong>Check:</strong> {chapter.success}</p></li>)}</ol></details>}
      {transcript.length > 0 && <details className="setup-walkthrough__transcript"><summary>Read the captions transcript</summary>{transcript.map((text, index) => <p key={index}>{text}</p>)}</details>}
    </section>
  );
}
