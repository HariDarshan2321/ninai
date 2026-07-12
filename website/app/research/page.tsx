import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "PACT research direction",
  description:
    "Explore Ninai's permission-first, provenance-backed approach to minimum sufficient context and the evaluation plan behind it.",
  alternates: { canonical: "/research/" },
  openGraph: {
    title: "PACT — Minimum sufficient context for AI memory",
    description: "Permission-first retrieval, provenance, and compact evidence packets.",
    url: "/research/",
    images: [
      {
        url: "/assets/og-image.png",
        width: 1200,
        height: 630,
        alt: "PACT minimum sufficient context research by Ninai",
      },
    ],
  },
};

const signals = [
  ["Lexical relevance", "0.34", "Does the fact address this request?"],
  ["Search position", "0.18", "How strongly did local retrieval surface it?"],
  ["Freshness", "0.16", "Is this memory current for its type?"],
  ["Importance", "0.14", "Was the outcome marked consequential?"],
  ["Confidence", "0.12", "How reliable was extraction or entry?"],
  ["Reinforcement", "0.06", "Has this memory proved useful before?"],
];

export default function ResearchPage() {
  return (
    <main id="main-content">
      <section className="research-hero">
        <div className="shell research-hero__inner">
          <div>
            <p className="section-label section-label--light">Research direction / PACT</p>
            <h1>The minimum context that still earns the answer.</h1>
          </div>
          <div className="research-hero__formula">
            <span>OBJECTIVE</span>
            <p>answer usefulness</p>
            <i>−</i>
            <p>token cost</p>
            <i>−</i>
            <p>disclosure risk</p>
            <small>subject to permission + provenance</small>
          </div>
        </div>
      </section>

      <section className="research-intro shell">
        <p className="research-intro__lead">
          More context is not automatically better context. Ninai explores retrieval as a
          constrained disclosure problem: preserve answer usefulness while reducing
          irrelevant tokens and unnecessary exposure.
        </p>
        <div className="research-disclaimer">
          <strong>Honest status</strong>
          <p>
            PACT is a working engineering method in the MVP. It is not presented as
            academically novel until it is evaluated against credible baselines.
          </p>
        </div>
      </section>

      <section className="research-pipeline shell">
        <p className="section-label">Pipeline / 01</p>
        <div className="pipeline-list">
          {[
            ["Identify", "Name the requesting client and record its purpose."],
            ["Constrain", "Resolve explicit grants before any search begins."],
            ["Retrieve", "Search only rows within the allowed scope set."],
            ["Rank", "Combine relevance, type-aware freshness, importance, and confidence."],
            ["Compose", "Select the highest-value evidence that fits the packet budget."],
            ["Log", "Record the exact memory IDs, scopes, purpose, and estimated tokens."],
          ].map(([title, copy], index) => (
            <article key={title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h2>{title}</h2>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="research-signals">
        <div className="shell">
          <div className="section-intro section-intro--split">
            <p className="section-label section-label--light">Current signals / 02</p>
            <div>
              <h2>Inspectable weights, not hidden magic.</h2>
              <p>
                The MVP uses deterministic weights that can be tested and changed. They
                are evaluation hypotheses, not immutable product truth.
              </p>
            </div>
          </div>
          <div className="signal-table">
            <div className="signal-table__head">
              <span>Signal</span><span>Weight</span><span>Question</span>
            </div>
            {signals.map(([signal, weight, question]) => (
              <div className="signal-table__row" key={signal}>
                <strong>{signal}</strong><span>{weight}</span><p>{question}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="research-evaluation shell">
        <p className="section-label">Evaluation plan / 03</p>
        <div className="research-evaluation__grid">
          <div>
            <h2>Compare the packet, not just the search result.</h2>
            <p>
              Ninai should be measured against full history, lexical top-k, semantic top-k,
              and future graph retrieval using the same questions and source evidence.
            </p>
          </div>
          <div className="metric-grid">
            {[
              ["Answer accuracy", "Did the model answer correctly?"],
              ["Context precision", "How much released context was useful?"],
              ["Temporal accuracy", "Did it prefer the current fact?"],
              ["Abstention", "Did it stop when evidence was missing?"],
              ["Scope leakage", "Did any forbidden memory appear?"],
              ["Token reduction", "How much context stayed local?"],
              ["Provenance", "Can each claim be traced?"],
              ["Latency", "Is the policy layer fast enough?"],
            ].map(([metric, copy]) => (
              <div key={metric}><strong>{metric}</strong><span>{copy}</span></div>
            ))}
          </div>
        </div>
      </section>

      <section className="research-next">
        <div className="shell research-next__grid">
          <div>
            <p className="section-label section-label--light">Next experiments / 04</p>
            <h2>Earn complexity one benchmark at a time.</h2>
          </div>
          <ol>
            <li><span>01</span> Build deterministic long-session fixtures.</li>
            <li><span>02</span> Measure lexical PACT against full history.</li>
            <li><span>03</span> Add a rebuildable local vector adapter.</li>
            <li><span>04</span> Test temporal supersession and conflict handling.</li>
            <li><span>05</span> Publish results—including failures.</li>
          </ol>
          <div className="research-next__cta">
            <Link className="button button--acid" href="/install/">Run the current MVP ↗</Link>
            <a className="button button--dark-line" href="mailto:hello@ninai.io?subject=PACT%20research">Discuss the research</a>
          </div>
        </div>
      </section>
    </main>
  );
}
