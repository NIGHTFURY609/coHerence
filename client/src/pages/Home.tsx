/* Field Notes / Civic Warmth: human-scale civic data, editorial asymmetry, and purposeful motion. */
import { AnimatePresence, motion, useMotionValue, useSpring } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Compass,
  ExternalLink,
  Menu,
  Minus,
  Plus,
  Route,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useLocation, Link } from "wouter";

gsap.registerPlugin(ScrollTrigger);

const IMAGE_URLS = {
  hero: "/manus-storage/coherence-hero-map_b920a41e.png",
  community: "/manus-storage/coherence-community_3e4d6ab5.jpg",
  facility: "/manus-storage/coherence-facility-reference_c02271b9.jpg",
  workforce: "/manus-storage/coherence-workforce-reference_e1e27b2e.jpg",
  mark: "/manus-storage/coherence-mark_62fd84c7.png",
};

const facilityFilters = [
  { id: "safety", label: "Motor", color: "clay", description: "Tremor, dwell, and missed clicks on undersized targets." },
  { id: "care", label: "Keyboard", color: "pistachio", description: "Tab order, unnamed controls, and traps that a pointer never meets." },
  { id: "health", label: "Vision", color: "blue", description: "Contrast, zoom, and what remains readable at 200%." },
  { id: "transit", label: "Baseline", color: "ink", description: "The unconstrained path every other profile is measured against." },
] as const;

const chapters = [
  { id: "top", label: "Signal" },
  { id: "gap", label: "The gap" },
  { id: "layers", label: "Two lenses" },
  { id: "impact", label: "What changes" },
];

function MagneticButton({
  children,
  href,
  variant = "ink",
  onClick,
}: {
  children: React.ReactNode;
  href?: string;
  variant?: "ink" | "clay" | "light";
  onClick?: () => void;
}) {
  const [, setLocation] = useLocation();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 350, damping: 24, mass: 0.25 });
  const springY = useSpring(y, { stiffness: 350, damping: 24, mass: 0.25 });

  const handleMove = (event: React.MouseEvent<HTMLAnchorElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX - (rect.left + rect.width / 2)) * 0.12);
    y.set((event.clientY - (rect.top + rect.height / 2)) * 0.12);
  };

  const reset = () => {
    x.set(0);
    y.set(0);
  };

  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (onClick) onClick();
    if (href && href.startsWith("/")) {
      event.preventDefault();
      setLocation(href);
    }
  };

  return (
    <motion.a
      href={href ?? "#"}
      className={`magnetic-button magnetic-${variant}`}
      style={{ x: springX, y: springY }}
      onMouseMove={handleMove}
      onMouseLeave={reset}
      onClick={handleClick}
    >
      <span>{children}</span>
      <ArrowUpRight size={16} strokeWidth={2.2} aria-hidden="true" />
    </motion.a>
  );
}

function Mark({ small = false }: { small?: boolean }) {
  return (
    <img
      src={IMAGE_URLS.mark}
      alt=""
      aria-hidden="true"
      className={small ? "brand-mark brand-mark-small" : "brand-mark"}
    />
  );
}

function CoherenceSymbol() {
  return (
    <svg className="coherence-symbol" viewBox="0 0 90 90" fill="none" aria-hidden="true">
      <path d="M17 55C26 55 27 25 46 25C65 25 61 64 76 64" stroke="currentColor" strokeWidth="7" strokeLinecap="round" />
      <path d="M17 68C31 68 34 39 49 39C63 39 62 75 76 75" stroke="currentColor" strokeWidth="7" strokeLinecap="round" opacity=".48" />
      <circle cx="74" cy="25" r="7" stroke="currentColor" strokeWidth="5" />
    </svg>
  );
}

function FacilityMap() {
  const [active, setActive] = useState<(typeof facilityFilters)[number]["id"]>("safety");
  const activeFilter = facilityFilters.find((filter) => filter.id === active) ?? facilityFilters[0];

  return (
    <div className="facility-visual" data-reveal>
      <div className="facility-image-wrap">
        <img src={IMAGE_URLS.facility} alt="Illustrated layout used as a stand-in for an interface under test" className="facility-image" />
        <div className="map-scan-line" aria-hidden="true" />
        <div className="facility-pin pin-one"><span className="pin-pulse" /><ShieldCheck size={14} /></div>
        <div className="facility-pin pin-two"><span className="pin-pulse" /><Sparkles size={14} /></div>
        <div className="facility-pin pin-three"><span className="pin-pulse" /><Route size={14} /></div>
        <div className="facility-gap-label">
          <span className="mini-label">Illustrative scan</span>
          <strong>Constraint gap</strong>
          <span>High baseline success · low constrained access</span>
        </div>
        <div className="facility-compass" aria-hidden="true"><Compass size={17} /><span>N</span></div>
      </div>
      <div className="facility-controls">
        <div className="control-heading">
          <span className="eyebrow">Layer the view</span>
          <span className="control-note">Tap a signal</span>
        </div>
        <div className="filter-list" role="tablist" aria-label="Facility map layers">
          {facilityFilters.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`facility-filter ${active === filter.id ? "is-active" : ""}`}
              onClick={() => setActive(filter.id)}
              role="tab"
              aria-selected={active === filter.id}
            >
              <span className={`filter-dot dot-${filter.color}`} />
              <span>{filter.label}</span>
              <ChevronRight size={15} aria-hidden="true" />
            </button>
          ))}
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={activeFilter.id}
            className="filter-description"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {activeFilter.description}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  );
}

function MiniContour({ className = "" }: { className?: string }) {
  return (
    <svg className={`mini-contour ${className}`} viewBox="0 0 300 120" fill="none" aria-hidden="true">
      <path d="M2 90C40 90 55 20 96 32C138 44 128 104 177 98C226 92 219 30 298 30" />
      <path d="M2 108C40 108 63 42 100 48C143 55 139 115 184 109C228 103 237 50 298 48" />
    </svg>
  );
}

function Home() {
  const rootRef = useRef<HTMLDivElement>(null);
  const lenisRef = useRef<Lenis | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeChapter, setActiveChapter] = useState("top");
  const [scrolled, setScrolled] = useState(false);
  const [cursorVisible, setCursorVisible] = useState(false);
  const cursorX = useMotionValue(-100);
  const cursorY = useMotionValue(-100);
  const cursorSpringX = useSpring(cursorX, { stiffness: 240, damping: 30 });
  const cursorSpringY = useSpring(cursorY, { stiffness: 240, damping: 30 });

  const scrollTo = (id: string) => {
    setMenuOpen(false);
    const target = document.getElementById(id);
    if (!target) return;
    if (lenisRef.current) {
      lenisRef.current.scrollTo(target, { offset: -18, duration: 0.9 });
      return;
    }
    target.scrollIntoView({ behavior: "auto", block: "start" });
  };

  const handleAnchorClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const anchor = (event.target as HTMLElement).closest<HTMLAnchorElement>("a[href^='#']");
    const id = anchor?.getAttribute("href")?.slice(1);
    if (!anchor || !id) return;
    event.preventDefault();
    scrollTo(id);
  };

  useEffect(() => {
    const finePointer = window.matchMedia("(pointer: fine)").matches;
    if (!finePointer) return;
    const handlePointerMove = (event: PointerEvent) => {
      cursorX.set(event.clientX - 7);
      cursorY.set(event.clientY - 7);
      setCursorVisible(true);
    };
    const handleLeave = () => setCursorVisible(false);
    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    document.body.addEventListener("mouseleave", handleLeave);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      document.body.removeEventListener("mouseleave", handleLeave);
    };
  }, [cursorX, cursorY]);

  useEffect(() => {
    let frame = 0;
    const handleScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setScrolled(window.scrollY > 28));
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ctx = gsap.context(() => {
      const sectionIds = chapters.map((chapter) => chapter.id);
      sectionIds.forEach((id) => {
        const element = document.getElementById(id);
        if (!element) return;
        ScrollTrigger.create({
          trigger: element,
          start: "top 48%",
          end: "bottom 48%",
          onEnter: () => setActiveChapter(id),
          onEnterBack: () => setActiveChapter(id),
        });
      });

      if (reduceMotion) return;
      gsap.from(".hero-reveal", { y: 28, opacity: 0, duration: 0.9, stagger: 0.08, ease: "power3.out", delay: 0.2 });
      gsap.to(".hero-contours", {
        yPercent: -11,
        ease: "none",
        scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
      });
      gsap.to(".hero-image", {
        scale: 1.04,
        ease: "none",
        scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
      });
      gsap.utils.toArray<HTMLElement>("[data-reveal]").forEach((element) => {
        gsap.from(element, {
          y: 34,
          opacity: 0,
          duration: 0.75,
          ease: "power3.out",
          scrollTrigger: { trigger: element, start: "top 82%", once: true },
        });
      });
      gsap.utils.toArray<HTMLElement>("[data-line-draw]").forEach((element) => {
        gsap.from(element, {
          scaleX: 0,
          transformOrigin: "left center",
          duration: 0.9,
          ease: "power3.inOut",
          scrollTrigger: { trigger: element, start: "top 84%", once: true },
        });
      });
    }, root);

    const lenis = reduceMotion ? null : new Lenis({ duration: 0.85, smoothWheel: true, syncTouch: false, anchors: false });
    lenisRef.current = lenis;
    const raf = (time: number) => {
      lenis?.raf(time * 1000);
      ScrollTrigger.update();
    };
    if (lenis) gsap.ticker.add(raf);
    return () => {
      if (lenis) gsap.ticker.remove(raf);
      lenis?.destroy();
      lenisRef.current = null;
      ctx.revert();
    };
  }, []);

  const lensItems = useMemo(
    () => [
      { index: "01", label: "Constrained capture", title: "See the route behind the statistic.", body: "Drive the same task as a baseline user, then as motor, keyboard, and vision constraints. The page does not change. The path does.", className: "lens-card-main", image: IMAGE_URLS.facility },
      { index: "02", label: "Fairness score", title: "Count who was never counted.", body: "Completion, time, errors, and friction become one integer. Findings name the control. Diagnosis comes after the number, never instead of it.", className: "lens-card-secondary", image: IMAGE_URLS.workforce },
    ],
    [],
  );

  return (
    <div ref={rootRef} className="site-shell" onClick={handleAnchorClick}>
      <motion.div
        className="cursor-orb"
        style={{ x: cursorSpringX, y: cursorSpringY, opacity: cursorVisible ? 1 : 0 }}
        aria-hidden="true"
      />
      <header className={`site-header ${scrolled ? "is-scrolled" : ""}`}>
        <a className="brand-lockup" href="#top" aria-label="CoHERence home">
          <Mark small />
          <span>Co<span className="brand-emphasis">HER</span>ence</span>
        </a>
        <nav className="desktop-nav" aria-label="Primary navigation">
          <a href="#gap">The gap</a>
          <a href="#layers">Two lenses</a>
          <a href="#impact">Why it matters</a>
          <Link href="/workspace">Workspace</Link>
        </nav>
        <div className="header-actions">
          <Link className="header-link desktop-only" href="/workspace">Open Workspace <ArrowUpRight size={15} /></Link>
          <button type="button" className="menu-toggle" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-controls="mobile-menu" aria-label={menuOpen ? "Close menu" : "Open menu"}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      <AnimatePresence>
        {menuOpen && (
          <motion.div id="mobile-menu" className="mobile-menu" initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
            <a href="#gap" onClick={() => setMenuOpen(false)}>The gap <ArrowUpRight size={17} /></a>
            <a href="#layers" onClick={() => setMenuOpen(false)}>Two lenses <ArrowUpRight size={17} /></a>
            <a href="#impact" onClick={() => setMenuOpen(false)}>Why it matters <ArrowUpRight size={17} /></a>
            <Link href="/workspace" onClick={() => setMenuOpen(false)}>Open Workspace <ArrowUpRight size={17} /></Link>
            <Link href="/workshop" onClick={() => setMenuOpen(false)}>Explore the signal <ArrowUpRight size={17} /></Link>
          </motion.div>
        )}
      </AnimatePresence>

      <aside className="coordinate-rail" aria-label="Page progress">
        <div className="rail-top"><span>COHERENCE / 01</span></div>
        <div className="rail-track">
          <div className="rail-line" />
          {chapters.map((chapter, index) => (
            <button
              type="button"
              key={chapter.id}
              className={`rail-chapter ${activeChapter === chapter.id ? "is-active" : ""}`}
              onClick={() => scrollTo(chapter.id)}
              aria-label={`Jump to ${chapter.label}`}
            >
              <span className="rail-dot">{String(index + 1).padStart(2, "0")}</span>
              <span className="rail-label">{chapter.label}</span>
            </button>
          ))}
        </div>
        <div className="rail-bottom"><span>Data / Care / Agency</span></div>
      </aside>

      <main>
        <section id="top" className="hero">
          <div className="hero-contours" aria-hidden="true"><MiniContour /><MiniContour className="contour-two" /></div>
          <div className="hero-copy-wrap">
            <div className="hero-kicker hero-reveal"><span className="kicker-dot" />Inclusive software testing playground</div>
            <h1 className="hero-title hero-reveal">Who does this software <em>work for</em>?</h1>
            <p className="hero-deck hero-reveal">CoHERence runs constrained users through a product, scores the gaps, and shows why a default path is harder for some people than others.</p>
            <div className="hero-actions hero-reveal">
              <MagneticButton href="/workspace" variant="clay">Open Workspace</MagneticButton>
              <a className="text-link" href="#gap">Why this matters <ArrowDownRight size={16} /></a>
            </div>
          </div>
          <div className="hero-visual hero-reveal">
            <div className="hero-image-frame">
              <img className="hero-image" src={IMAGE_URLS.hero} alt="Editorial map of routes used as a metaphor for interaction paths" />
              <div className="hero-image-shade" />
              <div className="hero-stamp"><span>FIELD NOTE</span><strong>01</strong></div>
              <div className="hero-coordinate"><span>20°35' N</span><span>72°52' E</span></div>
            </div>
            <div className="hero-caption"><span className="caption-line" />An atlas of who can finish the task, and who cannot.</div>
          </div>
          <div className="hero-bottom-note"><span>Scroll to the gap</span><ArrowDownRight size={15} /></div>
        </section>

        <section id="gap" className="gap-section section-pad">
          <div className="section-marker" data-reveal><span>01 / The gap</span><span>What is missing is measurable.</span></div>
          <div className="gap-grid">
            <div className="gap-intro" data-reveal>
              <p className="eyebrow">The default user</p>
              <h2>Every extra click is a data point.</h2>
            </div>
            <div className="gap-copy" data-reveal>
              <p className="lead-copy">A 24px pay button. A clickable div with no keyboard path. Instructions that only make sense if you can see them. These are not edge cases—they are signals of an interface planned around one unconstrained user.</p>
              <div className="inline-note"><CircleHelp size={17} /><span>CoHERence turns those observations into a traceable fairness score and a ranked list of findings.</span></div>
            </div>
          </div>
          <div className="gap-art" data-reveal>
            <div className="gap-art-background"><MiniContour /></div>
            <div className="gap-art-quote">“The missing keyboard path is a data point before it becomes a dropped task.”</div>
            <div className="gap-art-index"><span>FIELD NOTE</span><strong>02</strong></div>
          </div>
        </section>

        <section className="map-section section-pad section-dark" aria-labelledby="map-title">
          <div className="map-section-grid">
            <div className="map-copy" data-reveal>
              <p className="eyebrow eyebrow-light">Constraint profiles</p>
              <h2 id="map-title">See who the path actually serves.</h2>
              <p>Layer motor, keyboard, and vision constraints on the same task. A fairness gap is not a persona story—it is a measured difference in completion, time, and errors.</p>
              <div className="map-meta"><span className="meta-pulse" />Illustrative profile scan / workspace view</div>
            </div>
            <FacilityMap />
          </div>
        </section>

        <section id="layers" className="layers-section section-pad">
          <div className="section-marker" data-reveal><span>02 / Two lenses</span><span>One coherent view.</span></div>
          <div className="layers-heading" data-reveal>
            <h2>From scattered signals<br /><em>to shared ground.</em></h2>
            <p>The platform connects capture to score, so a designer can move from “does this work?” to “who does it work for, and why?”</p>
          </div>
          <div className="lens-stack">
            {lensItems.map((item, index) => (
              <motion.article
                key={item.index}
                className={`lens-card ${item.className}`}
                data-reveal
                whileHover={{ y: index === 0 ? -8 : 8, rotate: index === 0 ? -0.35 : 0.35 }}
                transition={{ type: "spring", stiffness: 220, damping: 18 }}
              >
                <div className="lens-card-image"><img src={item.image} alt="" aria-hidden="true" /><div className="lens-card-shade" /></div>
                <div className="lens-card-overlay">
                  <span className="card-index">{item.index}</span>
                  <span className="eyebrow eyebrow-light">{item.label}</span>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                  <button type="button" className="card-arrow" onClick={() => scrollTo("explore")} aria-label={`Explore ${item.label}`}><ArrowUpRight size={19} /></button>
                </div>
              </motion.article>
            ))}
          </div>
        </section>

        <section className="workforce-section section-pad section-tan" aria-labelledby="workforce-title">
          <div className="workforce-grid">
            <div className="workforce-visual" data-reveal>
              <img src={IMAGE_URLS.workforce} alt="Reviewing measured outcomes after a constrained run" />
              <div className="workforce-caption"><span>Outcome layer</span><strong>the people the path left behind</strong></div>
            </div>
            <div className="workforce-copy" data-reveal>
              <p className="eyebrow">What the report holds</p>
              <h2>Count the whole picture.</h2>
              <p className="lead-copy">Task completion. Extra time. Dead clicks. At a profile level those stop being anecdotes and become the fairness integer Hydrogen owns.</p>
              <div className="workforce-chart" aria-label="Illustrative outcome categories">
                <div className="chart-title"><span>Outcome view</span><span>Profile level</span></div>
                <div className="chart-rows">
                  <div className="chart-row"><span>Completion</span><span className="chart-bar"><i style={{ width: "82%" }} /></span><span>outcome</span></div>
                  <div className="chart-row"><span>Time</span><span className="chart-bar"><i style={{ width: "67%" }} /></span><span>friction</span></div>
                  <div className="chart-row"><span>Errors</span><span className="chart-bar"><i style={{ width: "44%" }} /></span><span>signal</span></div>
                </div>
                <div className="chart-footnote"><span className="chart-footnote-dot" />Illustrative categories from the fairness layer</div>
              </div>
            </div>
          </div>
        </section>

        <section id="impact" className="impact-section section-pad">
          <div className="section-marker" data-reveal><span>03 / What changes</span><span>Evidence becomes agency.</span></div>
          <div className="impact-heading" data-reveal>
            <div><p className="eyebrow">Why it matters</p><h2>A better test changes<br /><em>what gets built next.</em></h2></div>
            <p>CoHERence is unit testing for inclusive design. The goal is not another linter. It is a new default for whose path gets noticed.</p>
          </div>
          <div className="impact-grid">
            <div className="impact-card impact-card-feature" data-reveal>
              <div className="impact-card-top"><span>01</span><Route size={18} /></div>
              <h3>Fewer invisible trade-offs.</h3>
              <p>When the primary action is reachable by keyboard and large enough to hit, completion stops being a pointer privilege.</p>
              <div className="impact-graphic route-graphic"><span /><span /><span /><span /></div>
            </div>
            <div className="impact-card" data-reveal>
              <div className="impact-card-top"><span>02</span><ShieldCheck size={18} /></div>
              <h3>Stronger paths.</h3>
              <p>Named findings and a locked score close the gap between “it works here” and “it works for these users.”</p>
              <div className="impact-number">stay<span>+</span></div>
            </div>
            <div className="impact-card" data-reveal>
              <div className="impact-card-top"><span>03</span><Compass size={18} /></div>
              <h3>Repeatable by design.</h3>
              <p>Any page with a URL and a task can run the same capture, rules, and score.</p>
              <div className="impact-graphic repeat-graphic"><i /><i /><i /><i /><i /></div>
            </div>
          </div>
        </section>

        <section id="explore" className="explore-section section-pad section-clay">
          <div className="explore-contours" aria-hidden="true"><MiniContour /><MiniContour className="contour-two" /></div>
          <div className="explore-content" data-reveal>
            <p className="eyebrow eyebrow-light">The next layer is yours</p>
            <h2>Test for the life<br /><em>behind the default.</em></h2>
            <p>Put a product in the workspace, run constrained users through it, and watch the path as it happens.</p>
            <MagneticButton href="/workspace" variant="light">Open Workspace</MagneticButton>
          </div>
          <div className="explore-aside" data-reveal><CoherenceSymbol /><span>CoHERence / field note 03</span></div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-brand"><a className="brand-lockup" href="#top"><Mark small /><span>Co<span className="brand-emphasis">HER</span>ence</span></a><p>Inclusive testing for the people the default left out.</p></div>
        <div className="footer-links"><a href="#gap">The gap <ArrowUpRight size={14} /></a><a href="#layers">Two lenses <ArrowUpRight size={14} /></a><a href="#impact">Why it matters <ArrowUpRight size={14} /></a></div>
        <div className="footer-end"><span>Made for the paths that fail quietly.</span><span>© 2026 CoHERence</span></div>
      </footer>
    </div>
  );
}

export default Home;
