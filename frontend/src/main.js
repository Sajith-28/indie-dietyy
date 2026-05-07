import './index.css';

const API_URL = import.meta.env.VITE_API_URL !== undefined 
  ? import.meta.env.VITE_API_URL 
  : (import.meta.env.PROD ? '' : 'http://localhost:8000');

const STORAGE = {
  profile: 'app_profile',
  page: 'app_current_page',
  step: 'app_current_step',
  plan: 'app_last_plan',
  language: 'app_ui_language',
};

const DEFAULT_PROFILE = {
  name: '',
  age: 30,
  weight_kg: 70,
  height_cm: 170,
  state: 'Kerala',
  diet_type: 'Vegetarian',
  meat_prefs: [],
  goal: 'balanced',
  allergies: '',
  has_diabetes: false,
  blood_sugar: '',
  has_bp: false,
  systolic_bp: '',
  diastolic_bp: '',
  has_cholesterol: false,
  cholesterol: '',
};

const LANGUAGES = {
  en: 'English (English)',
  hi: 'Hindi (हिन्दी)',
  bn: 'Bengali (বাংলা)',
  te: 'Telugu (తెలుగు)',
  mr: 'Marathi (मराठी)',
  ta: 'Tamil (தமிழ்)',
  gu: 'Gujarati (ગુજરાતી)',
  kn: 'Kannada (ಕನ್ನಡ)',
  ml: 'Malayalam (മലയാളം)',
  pa: 'Punjabi (ਪੰਜਾਬੀ)',
  or: 'Odia (ଓଡ଼ିଆ)',
};

const STATES = [
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chhattisgarh',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
];

const MEATS = ['Chicken', 'Mutton', 'Beef', 'Pork', 'Fish', 'Crab', 'Prawns', 'Egg'];

const TEXT = {
  appBadge: 'Clinical Nutrition OS',
  title: 'Indie Dietyy',
  subtitle: 'Advanced Clinical AI Diet Planner',
  landingCopy: 'Personalized Indian diet plans shaped by region, preferences, allergies, BMI, and clinical markers.',
  startProfile: 'Start Clinical Profile',
  viewLastPlan: 'View Last Generated Plan',
  yourProfile: 'Your Profile',
  personalDetails: 'Personal Details',
  personalCopy: 'Start with the essentials. BMI updates live as your body metrics change.',
  name: 'Name',
  namePlaceholder: 'Enter your name',
  age: 'Age',
  weight: 'Weight (kg)',
  height: 'Height (cm)',
  calculatedBmi: 'Calculated BMI',
  regionDiet: 'Region & Diet',
  regionCopy: 'Tell the planner where your food habits live and what diet style it should respect.',
  state: 'State',
  dietType: 'Diet Type',
  goal: 'Your Goal',
  meatPrefs: 'Select Preferred Meats (Mandatory)',
  meatCopy: 'Choose the proteins you actually want included in the weekly plan.',
  clinical: 'Clinical Conditions (Optional)',
  clinicalCopy: 'Add clinical signals only if relevant. These values are sent to the AI backend for safer recommendations.',
  diabetes: 'Diabetes (Check to add)',
  bloodSugar: 'Fasting Blood Sugar (mg/dL)',
  bp: 'Blood Pressure (Check to add)',
  sysBp: 'Systolic BP (Upper, e.g. 120)',
  diaBp: 'Diastolic BP (Lower, e.g. 80)',
  cholesterolCheck: 'High Cholesterol (Check to add)',
  cholesterolLevel: 'Total Cholesterol (mg/dL)',
  allergies: 'Allergies (Free Text)',
  allergiesPlaceholder: 'e.g. Milk, Peanuts, Ghee...',
  review: 'Allergies & Review',
  reviewCopy: 'One last scan before the backend creates your personalized 7-day plan.',
  generate: 'Generate 7-Day Plan',
  generating: 'AI is generating plan...',
  translating: 'Translating UI...',
  next: 'Next',
  back: 'Back',
  backProfile: 'Back to Edit Profile',
  downloadPdf: 'Download PDF',
  emptyState: 'Fill out your medical profile to generate an intelligent, safe diet plan.',
  user: 'User',
  aiScore: 'AI Score',
  kcal: 'kcal',
  protein: 'Protein',
  carbs: 'Carbs',
  fat: 'Fat',
  fiber: 'Fiber',
  day: 'Day',
  ingredients: 'Ingredients',
  bmi: 'BMI',
  failed: 'Failed to connect to the AI Backend.',
  disclaimer: 'Clinical Disclaimer: This plan is AI-generated. Consult a registered dietitian before following if you have a diagnosed medical condition.',
  optVegetarian: 'Vegetarian',
  optNonVegetarian: 'Non-Vegetarian',
  optBoth: 'Both',
  optVegan: 'Vegan',
  optBalanced: 'Balanced Diet',
  optWeightLoss: 'Weight Loss',
  optWeightGain: 'Weight Gain',
  analyzingBmi: 'Analyzing BMI',
  checkingClinical: 'Checking clinical markers',
  balancingMeals: 'Balancing regional meals',
  optimizingMacros: 'Optimizing macros',
  preparingPlan: 'Preparing 7-day plan',
  savedPlan: 'Saved Plan',
  noPlanTitle: 'No diet plan yet',
  noPlanCopy: 'Create your profile first and Indie Dietyy will render the generated plan here.',
  planReady: 'Your clinical diet plan is ready',
};

const root = document.getElementById('root');

let state = {
  profile: readJson(STORAGE.profile, DEFAULT_PROFILE),
  page: localStorage.getItem(STORAGE.page) || 'landing',
  step: Number(localStorage.getItem(STORAGE.step) || 0),
  plan: readJson(STORAGE.plan, null),
  language: localStorage.getItem(STORAGE.language) || 'en',
  dynamicText: {},
  isTranslating: false,
  isGenerating: false,
  error: '',
  direction: 'forward', // Track navigation direction for cinematic transitions
};

if (state.page === 'result' && !state.plan) {
  state.page = 'landing';
}

const steps = [
  { id: 'personal', titleKey: 'personalDetails' },
  { id: 'region', titleKey: 'regionDiet' },
  { id: 'meat', titleKey: 'meatPrefs', conditional: true },
  { id: 'clinical', titleKey: 'clinical' },
  { id: 'review', titleKey: 'review' },
];

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return structuredCloneSafe(fallback);
    const parsed = JSON.parse(raw);
    return fallback && typeof fallback === 'object' && !Array.isArray(fallback)
      ? { ...fallback, ...parsed }
      : parsed;
  } catch {
    return structuredCloneSafe(fallback);
  }
}

function structuredCloneSafe(value) {
  return value === null ? null : JSON.parse(JSON.stringify(value));
}

function persist() {
  localStorage.setItem(STORAGE.profile, JSON.stringify(state.profile));
  localStorage.setItem(STORAGE.page, state.page);
  localStorage.setItem(STORAGE.step, String(state.step));
  localStorage.setItem(STORAGE.language, state.language);
  if (state.plan) {
    localStorage.setItem(STORAGE.plan, JSON.stringify(state.plan));
  }
}

function t(key) {
  return state.dynamicText[key] || TEXT[key] || key;
}

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function icon(name) {
  const icons = {
    spark: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l1.9 5.2L19 10l-5.1 1.8L12 17l-1.9-5.2L5 10l5.1-1.8L12 3z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z"/></svg>',
    globe: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 0 20"/><path d="M12 2a15.3 15.3 0 0 0 0 20"/></svg>',
    user: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="7" r="4"/></svg>',
    heart: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 12 5a5.5 5.5 0 0 0-10 3.5C2 10.8 3.5 12.5 5 14l7 7 7-7z"/><path d="M3.2 12H8l2-3 4 6 2-3h4.8"/></svg>',
    warning: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
    arrow: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>',
    next: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>',
    download: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>',
    utensils: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 2v7a4 4 0 0 0 4 4v9"/><path d="M7 2v20"/><path d="M11 2v7a4 4 0 0 1-4 4"/><path d="M21 15V2a5 5 0 0 0-5 5v6a2 2 0 0 0 2 2h3z"/></svg>',
    pulse: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>',
    check: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
  };
  return icons[name] || '';
}

function brandTitle(cssClass = '') {
  const title = t('title');
  // If title contains 'Dietyy' (English or translated), split it
  if (title.includes('Dietyy')) {
    const parts = title.split('Dietyy');
    return `<span class="brand-indie ${cssClass}">${esc(parts[0].trim())}</span> <span class="brand-dietyy ${cssClass}">${esc('Dietyy')}</span>`;
  }
  // For fully translated titles (non-English), render as-is
  return `<span class="${cssClass}">${esc(title)}</span>`;
}

function bmiValue() {
  const weight = Number.parseFloat(state.profile.weight_kg);
  const height = Number.parseFloat(state.profile.height_cm);
  if (!weight || !height) return '0.0';
  return (weight / ((height / 100) ** 2)).toFixed(1);
}

function showMeatStep() {
  return ['Non-Vegetarian', 'Both'].includes(state.profile.diet_type);
}

function visibleSteps() {
  return steps.filter((step) => !step.conditional || showMeatStep());
}

function currentStep() {
  const list = visibleSteps();
  if (state.step >= list.length) state.step = list.length - 1;
  if (state.step < 0) state.step = 0;
  return list[state.step];
}

function transitionTo(page, step = state.step) {
  const order = ['landing', 'wizard', 'generating', 'result'];
  const currentIndex = order.indexOf(state.page);
  const nextIndex = order.indexOf(page);
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  if (page === 'wizard' && state.page === 'wizard') {
    state.direction = step > state.step ? 'forward' : 'backward';
  } else {
    state.direction = nextIndex >= currentIndex ? 'forward' : 'backward';
  }

  if (state.page === 'generating' && page !== 'generating') {
    cursorController.sync('native_macos_cursor');
  }

  const currentView = document.querySelector('.view-wrapper');
  if (currentView) {
    currentView.classList.add(`exit-${state.direction}`);
  }

  const completeTransition = () => {
    state.page = page;
    state.step = step;
    state.error = '';
    persist();
    render();
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  };

  if (!currentView || reduceMotion) {
    completeTransition();
    return;
  }

  let finished = false;
  const finishOnce = () => {
    if (finished) return;
    finished = true;
    completeTransition();
  };

  currentView.addEventListener('animationend', finishOnce, { once: true });
  window.setTimeout(finishOnce, 420);
}

function render() {
  root.innerHTML = `
    <div class="app-shell">
      <div class="app-frame">
        ${renderHeader()}
        <div class="view-wrapper enter-${state.direction}">
          ${renderPage()}
        </div>
      </div>
    </div>
  `;
  bindEvents();
  bindHeroTilt();
  bindCinematicVideo();
  cursorController.sync(state.page === 'generating' ? 'loading_scope_cursor' : 'native_macos_cursor');
  
  if (state.page === 'generating') {
    bindMiniGame();
  }
}

let cinematicVideoAnimationId = null;

function bindCinematicVideo() {
  const video = document.getElementById('landing-video');
  if (!video) {
    if (cinematicVideoAnimationId) {
      cancelAnimationFrame(cinematicVideoAnimationId);
      cinematicVideoAnimationId = null;
    }
    return;
  }

  // Preload & wait for metadata
  if (video.readyState >= 1) {
    setupScrubbing(video);
  } else {
    video.addEventListener('loadedmetadata', () => setupScrubbing(video), { once: true });
  }
}

let globalScrubHandlersAttached = false;

// ─── VIRTUAL TIMELINE ENGINE ───────────────────────────────────
// Architecture: Raw scroll → targetProgress → smoothProgress (spring) → committedTime (seek-coalesced)
// This 3-layer pipeline ensures the video decoder is never thrashed.

const timeline = {
  target: 0,          // Raw scroll position (0-1), updated instantly on scroll
  smooth: 0,          // Spring-smoothed virtual position (0-1), updated every rAF
  velocity: 0,        // Current scroll velocity (for adaptive behavior)
  committed: -1,      // Last time actually written to video.currentTime
  lastScrollTs: 0,    // Timestamp of last scroll event
  lastSeekTs: 0,      // Timestamp of last successful seek commit
  isSeeking: false,   // True while the decoder is processing a seek
  duration: 0,        // Cached video duration
};

function setupScrubbing(video) {
  timeline.duration = video.duration;
  
  // Listen for decoder completion
  video.addEventListener('seeked', () => {
    timeline.isSeeking = false;
  });
  
  // ── MAIN ANIMATION LOOP ──────────────────────────────────────
  const tick = (now) => {
    const v = document.getElementById('landing-video');
    if (!v || !v.duration) {
      cinematicVideoAnimationId = requestAnimationFrame(tick);
      return;
    }
    
    // Cache duration (it can change if the video is still loading)
    timeline.duration = v.duration;
    
    // ── Layer 1: Spring smoothing ──
    // Critically-damped spring: smooth but no oscillation.
    // Factor 0.06 = very smooth glide. Higher = snappier but choppier.
    const delta = timeline.target - timeline.smooth;
    timeline.velocity = delta * 0.06;
    timeline.smooth += timeline.velocity;
    
    // Snap when extremely close (prevents infinite micro-convergence)
    if (Math.abs(delta) < 0.0005) {
      timeline.smooth = timeline.target;
      timeline.velocity = 0;
    }
    
    // ── Layer 2: Calculate ideal video time ──
    const idealTime = timeline.smooth * (timeline.duration - 0.01);
    
    // ── Layer 3: Seek coalescing ──
    // Only commit a seek if:
    //   1. The decoder is NOT busy processing a previous seek
    //   2. Enough time has passed since the last seek (adaptive interval)
    //   3. The difference is visually meaningful
    const timeSinceLastSeek = now - timeline.lastSeekTs;
    const diffFromCommitted = Math.abs(idealTime - timeline.committed);
    
    // Adaptive seek interval: heavier in the middle/end of the video
    // MP4 keyframes cluster at the start; middle has mostly P/B-frames
    // which are MUCH more expensive to decode via random seek.
    const progressRatio = timeline.smooth;
    const isHeavyZone = progressRatio > 0.15 && progressRatio < 0.95;
    const minSeekInterval = isHeavyZone ? 80 : 50; // ms between seeks
    const minSeekDiff = isHeavyZone ? 0.08 : 0.04; // seconds of video time
    
    const isScrolling = (now - timeline.lastScrollTs) < 200;
    
    if (
      !timeline.isSeeking &&
      timeSinceLastSeek > minSeekInterval &&
      diffFromCommitted > minSeekDiff
    ) {
      timeline.isSeeking = true;
      timeline.committed = idealTime;
      timeline.lastSeekTs = now;
      v.currentTime = idealTime;
    }
    
    // ── Settling: when scrolling stops, gently converge to exact target ──
    if (
      !isScrolling &&
      !timeline.isSeeking &&
      diffFromCommitted > 0.01 &&
      timeSinceLastSeek > 250
    ) {
      timeline.isSeeking = true;
      timeline.committed = idealTime;
      timeline.lastSeekTs = now;
      v.currentTime = idealTime;
    }
    
    cinematicVideoAnimationId = requestAnimationFrame(tick);
  };
  
  if (cinematicVideoAnimationId) cancelAnimationFrame(cinematicVideoAnimationId);
  cinematicVideoAnimationId = requestAnimationFrame(tick);

  // ── EVENT LISTENERS (attached once) ──────────────────────────
  if (!globalScrubHandlersAttached) {
    globalScrubHandlersAttached = true;
    
    // Desktop parallax tilt (mousemove only moves the text, NOT the video)
    window.addEventListener('mousemove', (e) => {
      if (window.innerWidth <= 768) return;
      
      const content = document.querySelector('.hero-content');
      const xPos = e.clientX / window.innerWidth;
      const yPos = e.clientY / window.innerHeight;
      
      if (content) {
        const tiltX = (0.5 - yPos) * 12;
        const tiltY = (xPos - 0.5) * 12;
        content.style.transform = `perspective(1200px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(1.02, 1.02, 1.02)`;
      }
    }, { passive: true });
    
    // Reset parallax when mouse leaves
    document.addEventListener('mouseleave', () => {
      const content = document.querySelector('.hero-content');
      if (content && window.innerWidth > 768) {
        content.style.transform = 'perspective(1200px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
      }
    });

    // ── SCROLL HANDLER ──
    // Only sets the raw target. Never touches the video directly.
    window.addEventListener('scroll', () => {
      const container = document.getElementById('cinematic-landing');
      if (!container) return;
      
      const maxScroll = container.offsetHeight - window.innerHeight;
      if (maxScroll <= 0) return;
      
      timeline.target = Math.max(0, Math.min(1, window.scrollY / maxScroll));
      timeline.lastScrollTs = performance.now();
    }, { passive: true });
  }
}

function renderHeader() {
  return `
    <header class="app-header">
      <div class="brand-lockup">
        <img class="brand-mark" src="/logo.png" alt="Indie Dietyy Logo" aria-hidden="true" style="padding: 0; object-fit: cover; border: 1px solid rgba(255,255,255,0.1);" />
        <div>
          <h1 class="brand-title">${brandTitle()}</h1>
          <p class="brand-subtitle">${esc(t('subtitle'))}</p>
        </div>
      </div>
      <div class="header-actions">
        ${state.page !== 'landing' ? `<button class="btn btn-secondary" type="button" data-action="landing" aria-label="Home">${icon('arrow')} Home</button>` : ''}
        <label class="language-control" for="language-switcher">
          ${icon('globe')}
          <select id="language-switcher" aria-label="Language">
            ${Object.entries(LANGUAGES).map(([code, label]) => `
              <option value="${code}" ${state.language === code ? 'selected' : ''}>${esc(label)}</option>
            `).join('')}
          </select>
          ${state.isTranslating ? '<span class="spinner" aria-label="Translating"></span>' : ''}
        </label>
      </div>
    </header>
  `;
}

function renderPage() {
  if (state.page === 'wizard') return renderWizard();
  if (state.page === 'generating') return renderGenerating();
  if (state.page === 'result') return renderResult();
  return renderLanding();
}

function renderLanding() {
  return `
    <div class="landing-page-wrapper">
      <main class="view cinematic-landing" id="cinematic-landing">
        <div class="video-container" id="video-container">
          <video id="landing-video" class="cinematic-video" preload="auto" muted playsinline>
            <source media="(max-width: 768px)" src="/Animation/Mobile.mp4" type="video/mp4">
            <source src="/Animation/desktop.mp4" type="video/mp4">
          </video>
          <div class="landing-overlay">
            <div class="hero-content">
              <span class="hero-kicker">${icon('spark')} ${esc(t('appBadge'))}</span>
              <h2 class="hero-title">${brandTitle('shiny')}</h2>
              <p class="hero-copy">${esc(t('landingCopy'))}</p>
              <div class="hero-actions">
                <button class="btn btn-primary" type="button" data-action="start">${icon('next')} ${esc(t('startProfile'))}</button>
                ${state.plan ? `<button class="btn btn-secondary" id="view-last-plan-btn" type="button" data-action="result">${icon('utensils')} ${esc(t('viewLastPlan'))}</button>` : ''}
              </div>
              <div class="interaction-hint">
                <span class="hint-desktop">${icon('pulse')} Scroll down to explore</span>
                <span class="hint-mobile">${icon('pulse')} Scroll down to explore</span>
              </div>
            </div>
          </div>
        </div>
        <div class="scroll-space" aria-hidden="true"></div>
      </main>
      
      <section class="about-section view">
        <div class="about-container">
          <div class="about-header">
            <span class="section-kicker">${icon('spark')} The Engine</span>
            <h2 class="about-title">Intelligent Clinical Nutrition</h2>
            <p class="about-copy">
              Indie Dietyy is a high-performance, clinical-grade AI diet planner engineered specifically for authentic regional Indian cuisine. 
              It leverages advanced generative AI to create customized, medically safe nutrition protocols that respect cultural dietary patterns, addressing complex conditions like diabetes, hypertension, and cholesterol.
            </p>
          </div>
          
          <div class="developer-credits">
            <h3 class="credits-title">Engineered By</h3>
            <div class="dev-profiles">
              <div class="dev-profile panel">
                <div class="dev-avatar">${icon('user')}</div>
                <div class="dev-info">
                  <h4>Sajith Ahamed</h4>
                  <span>Lead AI & Full Stack Developer</span>
                </div>
              </div>
              <div class="dev-profile panel">
                <div class="dev-avatar">${icon('user')}</div>
                <div class="dev-info">
                  <h4>Kanagavel</h4>
                  <span>Core Developer</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderWizard() {
  const list = visibleSteps();
  const active = currentStep();
  return `
    <main class="view wizard-layout">
      <aside class="panel step-rail" aria-label="Profile steps">
        <p class="rail-title">${esc(t('yourProfile'))}</p>
        <div class="step-list">
          ${list.map((step, index) => `
            <div class="step-pill ${index === state.step ? 'is-active' : ''} ${index < state.step ? 'is-done' : ''}">
              <span class="step-number">${index < state.step ? icon('check') : index + 1}</span>
              <strong>${esc(t(step.titleKey))}</strong>
            </div>
          `).join('')}
        </div>
      </aside>
      <section class="panel wizard-card">
        <form id="profile-form" novalidate>
          <div class="wizard-card-inner" data-step="${esc(active.id)}">
            ${renderStep(active.id)}
            ${state.error ? `<div class="error-box" role="alert">${esc(state.error)}</div>` : ''}
            ${renderWizardActions()}
          </div>
        </form>
      </section>
    </main>
  `;
}

function renderStep(stepId) {
  if (stepId === 'personal') return renderPersonalStep();
  if (stepId === 'region') return renderRegionStep();
  if (stepId === 'meat') return renderMeatStep();
  if (stepId === 'clinical') return renderClinicalStep();
  return renderReviewStep();
}

function renderStepHeader(kicker, title, copy, extra = '') {
  return `
    <div class="step-header">
      <div>
        <span class="section-kicker">${kicker}</span>
        <h2 class="step-title">${esc(title)}</h2>
        <p class="step-copy">${esc(copy)}</p>
      </div>
      ${extra}
    </div>
  `;
}

function renderPersonalStep() {
  return `
    ${renderStepHeader(`${icon('user')} ${esc(t('yourProfile'))}`, t('personalDetails'), t('personalCopy'), `
      <div class="bmi-chip"><span>${esc(t('calculatedBmi'))}</span><strong>${esc(bmiValue())}</strong></div>
    `)}
    <div class="form-grid">
      ${field('input-name', 'name', t('name'), 'text', state.profile.name, t('namePlaceholder'), true, 'full')}
      ${field('input-age', 'age', t('age'), 'number', state.profile.age, '', true)}
      ${field('input-weight', 'weight_kg', t('weight'), 'number', state.profile.weight_kg, '', true)}
      ${field('input-height', 'height_cm', t('height'), 'number', state.profile.height_cm, '', true)}
    </div>
  `;
}

function renderRegionStep() {
  return `
    ${renderStepHeader(`${icon('utensils')} ${esc(t('regionDiet'))}`, t('regionDiet'), t('regionCopy'))}
    <div class="form-grid">
      <div class="field">
        <label for="select-state">${esc(t('state'))}</label>
        <select class="select" id="select-state" name="state">
          ${STATES.map((item) => `<option value="${esc(item)}" ${state.profile.state === item ? 'selected' : ''}>${esc(item)}</option>`).join('')}
        </select>
      </div>
      <div class="field">
        <label for="select-diet-type">${esc(t('dietType'))}</label>
        <select class="select" id="select-diet-type" name="diet_type">
          ${option('Vegetarian', t('optVegetarian'), state.profile.diet_type)}
          ${option('Non-Vegetarian', t('optNonVegetarian'), state.profile.diet_type)}
          ${option('Both', t('optBoth'), state.profile.diet_type)}
          ${option('Vegan', t('optVegan'), state.profile.diet_type)}
        </select>
      </div>
      <div class="field full">
        <label for="select-goal">${esc(t('goal'))}</label>
        <select class="select" id="select-goal" name="goal">
          ${option('balanced', t('optBalanced'), state.profile.goal)}
          ${option('weight_loss', t('optWeightLoss'), state.profile.goal)}
          ${option('weight_gain', t('optWeightGain'), state.profile.goal)}
        </select>
      </div>
    </div>
  `;
}

function renderMeatStep() {
  return `
    ${renderStepHeader(`${icon('utensils')} ${esc(t('dietType'))}`, t('meatPrefs'), t('meatCopy'))}
    <div class="chip-grid">
      ${MEATS.map((meat) => `
        <label class="chip">
          <input type="checkbox" name="meat_prefs" value="${esc(meat)}" ${state.profile.meat_prefs.includes(meat) ? 'checked' : ''}>
          <span>${esc(meat)}</span>
        </label>
      `).join('')}
    </div>
  `;
}

function renderClinicalStep() {
  return `
    ${renderStepHeader(`${icon('heart')} Medical Signals`, t('clinical'), t('clinicalCopy'))}
    <div class="clinical-grid">
      <label class="checkbox-card">
        <input id="check-diabetes" type="checkbox" name="has_diabetes" ${state.profile.has_diabetes ? 'checked' : ''}>
        <span>${esc(t('diabetes'))}</span>
      </label>
      ${state.profile.has_diabetes ? `
        <div class="conditional-fields">
          ${field('input-blood-sugar', 'blood_sugar', t('bloodSugar'), 'number', state.profile.blood_sugar, t('bloodSugar'), true, 'full')}
        </div>` : ''}

      <label class="checkbox-card">
        <input id="check-bp" type="checkbox" name="has_bp" ${state.profile.has_bp ? 'checked' : ''}>
        <span>${esc(t('bp'))}</span>
      </label>
      ${state.profile.has_bp ? `
        <div class="conditional-fields">
          ${field('input-systolic', 'systolic_bp', t('sysBp'), 'number', state.profile.systolic_bp, t('sysBp'), true)}
          ${field('input-diastolic', 'diastolic_bp', t('diaBp'), 'number', state.profile.diastolic_bp, t('diaBp'), true)}
        </div>` : ''}

      <label class="checkbox-card">
        <input id="check-cholesterol" type="checkbox" name="has_cholesterol" ${state.profile.has_cholesterol ? 'checked' : ''}>
        <span>${esc(t('cholesterolCheck'))}</span>
      </label>
      ${state.profile.has_cholesterol ? `
        <div class="conditional-fields">
          ${field('input-cholesterol', 'cholesterol', t('cholesterolLevel'), 'number', state.profile.cholesterol, t('cholesterolLevel'), true, 'full')}
        </div>` : ''}
    </div>
  `;
}

function renderReviewStep() {
  const profile = state.profile;
  return `
    ${renderStepHeader(`${icon('warning')} Safety Review`, t('review'), t('reviewCopy'))}
    <div class="field">
      <label for="input-allergies">${icon('warning')} ${esc(t('allergies'))}</label>
      <textarea class="textarea" id="input-allergies" name="allergies" rows="3" placeholder="${esc(t('allergiesPlaceholder'))}">${esc(profile.allergies)}</textarea>
    </div>
    <div class="review-grid" aria-label="Profile review">
      ${reviewItem(t('name'), profile.name || '-')}
      ${reviewItem(t('calculatedBmi'), bmiValue())}
      ${reviewItem(t('state'), profile.state)}
      ${reviewItem(t('dietType'), profile.diet_type)}
      ${reviewItem(t('goal'), goalLabel(profile.goal))}
      ${reviewItem(t('meatPrefs'), profile.meat_prefs.length ? profile.meat_prefs.join(', ') : '-')}
      ${reviewItem(t('clinical'), clinicalSummary())}
      ${reviewItem(t('allergies'), profile.allergies || '-')}
    </div>
  `;
}

function renderWizardActions() {
  const list = visibleSteps();
  const isLast = state.step === list.length - 1;
  return `
    <div class="wizard-actions">
      <button class="btn btn-secondary" type="button" data-action="${state.step === 0 ? 'landing' : 'prev'}">${icon('arrow')} ${esc(t('back'))}</button>
      <button class="btn btn-primary" id="${isLast ? 'submit-btn' : 'next-step-btn'}" type="button" data-action="${isLast ? 'submit' : 'next'}" ${state.isTranslating || state.isGenerating ? 'disabled' : ''}>
        ${state.isGenerating ? '<span class="spinner"></span>' : icon(isLast ? 'spark' : 'next')}
        ${esc(state.isTranslating ? t('translating') : isLast ? t('generate') : t('next'))}
      </button>
    </div>
  `;
}

function renderGenerating() {
  return `
    <main class="view loading-stage">
      <div id="mini-game-container" class="mini-game-container">
        <div class="game-ui">
          <div class="game-title">Tap the Fats!</div>
          <div class="game-score">Score: <span id="game-score">0</span></div>
        </div>
      </div>
      <section class="loading-overlay">
        <div class="scanner" aria-hidden="true"><div class="scanner-core"></div></div>
        <span class="section-kicker">${icon('spark')} AI Clinical Engine</span>
        <h2 class="step-title">${esc(t('generating'))}</h2>
        <div class="status-lines" aria-label="Generation progress">
          <div class="status-line">${esc(t('analyzingBmi'))}</div>
          <div class="status-line">${esc(t('checkingClinical'))}</div>
          <div class="status-line">${esc(t('balancingMeals'))}</div>
          <div class="status-line">${esc(t('optimizingMacros'))}</div>
          <div class="status-line">${esc(t('preparingPlan'))}</div>
        </div>
        ${state.error ? `<div class="error-box" role="alert">${esc(state.error)}</div>` : ''}
      </section>
    </main>
  `;
}

function renderResult() {
  if (!state.plan) {
    return `
      <main class="view empty-plan panel">
        <h2>${esc(t('noPlanTitle'))}</h2>
        <p class="step-copy">${esc(t('noPlanCopy'))}</p>
        <div class="hero-actions" style="justify-content:center;margin-top:22px">
          <button class="btn btn-primary" type="button" data-action="start">${icon('next')} ${esc(t('startProfile'))}</button>
        </div>
      </main>
    `;
  }

  const plan = state.plan;
  const metadata = plan.metadata || {};
  const classifications = metadata.medical_classifications || {};
  return `
    <main class="view">
      <div class="result-actions">
        <button class="btn btn-secondary" id="back-to-profile-btn" type="button" data-action="wizard">${icon('arrow')} ${esc(t('backProfile'))}</button>
        <button class="btn btn-primary" id="download-pdf-btn" type="button" data-action="pdf">${icon('download')} ${esc(t('downloadPdf'))}</button>
      </div>

      <section class="print-surface" id="diet-plan-print">
        <div class="summary-card">
          <span class="section-kicker">${icon('pulse')} ${esc(t('savedPlan'))}</span>
          <h2 class="summary-title">${esc(metadata.title || t('planReady'))}</h2>
          <div class="badge-row">
            <span class="badge">${esc(t('user'))}: ${esc(metadata.user_name || state.profile.name || 'Guest')}</span>
            <span class="badge">${esc(t('bmi'))}: ${esc(metadata.bmi ?? bmiValue())}</span>
            ${Object.entries(classifications).map(([key, value]) => `
              <span class="badge caution">${esc(key.replaceAll('_', ' '))}: ${esc(value)}</span>
            `).join('')}
          </div>
          <p class="disclaimer">${esc(metadata.disclaimer || t('disclaimer'))}</p>
        </div>
        ${renderDietDays(plan.diet_plan || {})}
      </section>
    </main>
  `;
}

function renderDietDays(dietPlan) {
  const entries = Object.entries(dietPlan);
  if (!entries.length) {
    return `<div class="day-card"><h3>${esc(t('noPlanTitle'))}</h3><p class="ingredients">${esc(t('noPlanCopy'))}</p></div>`;
  }
  return entries.map(([day, meals]) => `
    <article class="day-card">
      <h3>${esc(day)}</h3>
      ${Object.entries(meals || {}).map(([mealType, meal]) => renderMeal(mealType, meal || {})).join('')}
    </article>
  `).join('');
}

function renderMeal(mealType, meal) {
  return `
    <section class="meal-slot">
      <div class="meal-title-row">
        <span class="meal-type">${esc(mealType)}</span>
        <span class="badge">${esc(t('aiScore'))}: ${esc(meal.ai_score ?? '-')}/100</span>
      </div>
      <p class="meal-name">${esc(meal.meal_name || '-')}</p>
      <div class="macro-row">
        <span class="macro">Calories: ${esc(meal.calories ?? '-')} ${esc(t('kcal'))}</span>
        <span class="macro">${esc(t('protein'))}: ${esc(meal.protein_g ?? '-')}g</span>
        <span class="macro">${esc(t('carbs'))}: ${esc(meal.carbs_g ?? '-')}g</span>
        <span class="macro">${esc(t('fat'))}: ${esc(meal.fat_g ?? '-')}g</span>
        ${meal.fiber_g !== undefined && meal.fiber_g !== null ? `<span class="macro">${esc(t('fiber'))}: ${esc(meal.fiber_g)}g</span>` : ''}
      </div>
      <p class="ingredients"><strong>${esc(t('ingredients'))}:</strong> ${esc(meal.ingredients || '-')}</p>
    </section>
  `;
}

function field(id, name, label, type, value, placeholder = '', required = false, className = '') {
  return `
    <div class="field ${className}">
      <label for="${esc(id)}">${esc(label)}</label>
      <input class="input" id="${esc(id)}" name="${esc(name)}" type="${esc(type)}" value="${esc(value)}" placeholder="${esc(placeholder)}" ${required ? 'required' : ''}>
    </div>
  `;
}

function option(value, label, selected) {
  return `<option value="${esc(value)}" ${selected === value ? 'selected' : ''}>${esc(label)}</option>`;
}

function reviewItem(label, value) {
  return `<div class="review-item"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}

function goalLabel(goal) {
  return {
    balanced: t('optBalanced'),
    weight_loss: t('optWeightLoss'),
    weight_gain: t('optWeightGain'),
  }[goal] || goal;
}

function clinicalSummary() {
  const items = [];
  if (state.profile.has_diabetes) items.push(`${t('diabetes')}: ${state.profile.blood_sugar || '-'}`);
  if (state.profile.has_bp) items.push(`${t('bp')}: ${state.profile.systolic_bp || '-'}/${state.profile.diastolic_bp || '-'}`);
  if (state.profile.has_cholesterol) items.push(`${t('cholesterolCheck')}: ${state.profile.cholesterol || '-'}`);
  return items.length ? items.join(' | ') : '-';
}

function bindEvents() {
  const language = document.getElementById('language-switcher');
  if (language) {
    language.addEventListener('change', async (event) => {
      state.language = event.target.value;
      localStorage.setItem(STORAGE.language, state.language);
      await loadTranslations();
      render();
    });
  }

  root.querySelectorAll('[data-action]').forEach((element) => {
    element.addEventListener('click', handleAction);
  });

  const form = document.getElementById('profile-form');
  if (form) {
    form.addEventListener('input', handleFormChange);
    form.addEventListener('change', handleFormChange);
    form.addEventListener('submit', (event) => event.preventDefault());
  }
}

function handleAction(event) {
  const action = event.currentTarget.dataset.action;
  if (action === 'start') {
    transitionTo('wizard', 0);
  } else if (action === 'landing') {
    transitionTo('landing', 0);
  } else if (action === 'result') {
    transitionTo('result');
  } else if (action === 'wizard') {
    transitionTo('wizard', Math.min(state.step, visibleSteps().length - 1));
  } else if (action === 'prev') {
    transitionTo('wizard', Math.max(0, state.step - 1));
  } else if (action === 'next') {
    goNext();
  } else if (action === 'submit') {
    submitProfile();
  } else if (action === 'pdf') {
    downloadPdf();
  }
}

function handleFormChange(event) {
  const target = event.target;
  if (!target.name) return;

  if (target.name === 'meat_prefs') {
    const next = new Set(state.profile.meat_prefs);
    if (target.checked) next.add(target.value);
    else next.delete(target.value);
    state.profile.meat_prefs = Array.from(next);
  } else if (target.type === 'checkbox') {
    state.profile[target.name] = target.checked;
  } else {
    state.profile[target.name] = target.value;
  }

  if (!showMeatStep()) {
    state.profile.meat_prefs = [];
  }

  persist();
  if (['has_diabetes', 'has_bp', 'has_cholesterol', 'diet_type'].includes(target.name)) {
    render();
  } else if (['weight_kg', 'height_cm'].includes(target.name)) {
    const chip = document.querySelector('.bmi-chip strong');
    if (chip) chip.textContent = bmiValue();
  }
}

function validateCurrentStep() {
  const active = currentStep().id;
  const requiredIds = {
    personal: ['input-name', 'input-age', 'input-weight', 'input-height'],
    region: ['select-state', 'select-diet-type', 'select-goal'],
    meat: [],
    clinical: [],
    review: [],
  }[active] || [];

  if (active === 'meat' && showMeatStep() && state.profile.meat_prefs.length === 0) {
    state.error = t('meatPrefs');
    render();
    return false;
  }

  if (active === 'clinical') {
    if (state.profile.has_diabetes) requiredIds.push('input-blood-sugar');
    if (state.profile.has_bp) requiredIds.push('input-systolic', 'input-diastolic');
    if (state.profile.has_cholesterol) requiredIds.push('input-cholesterol');
  }

  for (const id of requiredIds) {
    const element = document.getElementById(id);
    if (element && !element.checkValidity()) {
      element.reportValidity();
      return false;
    }
  }

  state.error = '';
  return true;
}

function goNext() {
  if (!validateCurrentStep()) return;
  const nextStep = Math.min(state.step + 1, visibleSteps().length - 1);
  transitionTo('wizard', nextStep);
}

function buildPayload() {
  const profile = state.profile;
  const conditions = [];
  if (profile.has_diabetes) conditions.push('diabetes');
  if (profile.has_bp) conditions.push('hypertension');
  if (profile.has_cholesterol) conditions.push('cholesterol');

  return {
    name: profile.name,
    age: Number.parseInt(profile.age, 10),
    weight_kg: Number.parseFloat(profile.weight_kg),
    height_cm: Number.parseFloat(profile.height_cm),
    state: profile.state,
    diet_type: profile.diet_type,
    meat_prefs: profile.meat_prefs,
    goal: profile.goal,
    language: state.language,
    allergies: profile.allergies,
    conditions,
    blood_sugar: profile.has_diabetes ? Number.parseFloat(profile.blood_sugar) : null,
    systolic_bp: profile.has_bp ? Number.parseFloat(profile.systolic_bp) : null,
    diastolic_bp: profile.has_bp ? Number.parseFloat(profile.diastolic_bp) : null,
    cholesterol: profile.has_cholesterol ? Number.parseFloat(profile.cholesterol) : null,
  };
}

async function submitProfile() {
  if (!validateCurrentStep() || state.isTranslating) return;
  state.isGenerating = true;
  state.error = '';
  state.page = 'generating';
  persist();
  render();

  try {
    const response = await fetch(`${API_URL}/api/generate_plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPayload()),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data?.detail || t('failed'));
    }

    state.plan = data;
    localStorage.setItem(STORAGE.plan, JSON.stringify(data));
    state.isGenerating = false;
    transitionTo('result');
  } catch (error) {
    state.isGenerating = false;
    state.error = error.message || t('failed');
    state.page = 'wizard';
    persist();
    render();
  }
}

async function loadTranslations() {
  state.dynamicText = {};
  if (state.language === 'en') {
    state.isTranslating = false;
    return;
  }

  // Bump version to v3 to bust stale caches from old (incomplete) locale files
  const cacheKey = `ui_cache_vanilla_v3_${state.language}`;
  try {
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      state.dynamicText = JSON.parse(cached);
      state.isTranslating = false;
      return;
    }
  } catch {
    localStorage.removeItem(cacheKey);
  }

  state.isTranslating = true;
  render();

  try {
    // Bust CDN/browser cache by appending build timestamp
    const response = await fetch(`/locales/ui_${state.language}.json?v=3`);
    if (!response.ok) throw new Error('Static UI translations not found');
    const data = await response.json();
    
    // Map every TEXT key: look up the English value in the locale dict
    // Falls back to the English value if not translated
    const entries = Object.entries(TEXT);
    state.dynamicText = Object.fromEntries(
      entries.map(([key, englishValue]) => [key, data[englishValue] || englishValue])
    );
    localStorage.setItem(cacheKey, JSON.stringify(state.dynamicText));
  } catch (err) {
    console.error('[i18n] Failed to load translations:', err);
    state.dynamicText = {};
  } finally {
    state.isTranslating = false;
    persist();
  }
}

async function downloadPdf() {
  const element = document.getElementById('diet-plan-print');
  if (!element) return;
  const safeName = (state.profile.name || state.plan?.metadata?.user_name || 'Guest')
    .replace(/[^a-z0-9_-]+/gi, '_')
    .replace(/^_+|_+$/g, '') || 'Guest';

  const { default: html2pdf } = await import('html2pdf.js');
  html2pdf()
    .set({
      margin: 0.45,
      filename: `Indie_Dietyy_Plan_${safeName}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, backgroundColor: '#050812' },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' },
      pagebreak: { mode: ['css', 'legacy'] },
    })
    .from(element)
    .save();
}

function bindHeroTilt() {
  const device = document.getElementById('hero-device');
  if (!device || window.matchMedia('(pointer: coarse)').matches) return;

  device.addEventListener('pointermove', (event) => {
    const rect = device.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const nx = x / rect.width - 0.5;
    const ny = y / rect.height - 0.5;
    device.style.setProperty('--rx', `${(-ny * 9).toFixed(2)}deg`);
    device.style.setProperty('--ry', `${(nx * 12).toFixed(2)}deg`);
    device.style.setProperty('--mx', `${x}px`);
    device.style.setProperty('--my', `${y}px`);
  });

  device.addEventListener('pointerleave', () => {
    device.style.setProperty('--rx', '0deg');
    device.style.setProperty('--ry', '0deg');
    device.style.setProperty('--mx', '50%');
    device.style.setProperty('--my', '30%');
  });
}

let miniGameLoopId = null;

function bindMiniGameLegacy() {
  const container = document.getElementById('mini-game-container');
  if (!container) return;

  let score = 0;
  let fatSpawnRate = 1200; // start slow
  let lastSpawn = 0;
  const fats = ['🍔', '🍩', '🍕', '🥓', '🍟', '🌭', '🍗'];
  const veggies = ['🥦', '🥕', '🥬', '🥑', '🥒', '🥗'];
  
  const scoreBoard = document.getElementById('game-score');

  const spawnFat = (now) => {
    if (state.page !== 'generating') {
      if (miniGameLoopId) cancelAnimationFrame(miniGameLoopId);
      return;
    }
    
    if (now - lastSpawn > fatSpawnRate) {
      lastSpawn = now;
      fatSpawnRate = Math.max(300, fatSpawnRate - 60); // difficulty curve

      const fat = document.createElement('div');
      fat.className = 'fat-enemy';
      fat.innerText = fats[Math.floor(Math.random() * fats.length)];
      // Random X position between 10% and 90%
      fat.style.left = Math.random() * 80 + 10 + '%';
      // Random fall speed
      fat.style.animationDuration = Math.random() * 2 + 2.5 + 's';
      
      fat.addEventListener('mousedown', (e) => {
        e.preventDefault();
        score++;
        if (scoreBoard) scoreBoard.innerText = score;
        
        const rect = fat.getBoundingClientRect();
        fat.remove();
        
        // Explosion of veggies
        for (let i = 0; i < 4; i++) {
          const veg = document.createElement('div');
          veg.className = 'veggie-burst';
          veg.innerText = veggies[Math.floor(Math.random() * veggies.length)];
          veg.style.left = rect.left + 'px';
          veg.style.top = rect.top + 'px';
          // Random scatter velocities
          veg.style.setProperty('--tx', (Math.random() * 160 - 80) + 'px');
          veg.style.setProperty('--ty', (Math.random() * -120 - 40) + 'px');
          document.body.appendChild(veg);
          setTimeout(() => veg.remove(), 800);
        }
      });
      
      // Touch support
      fat.addEventListener('touchstart', (e) => {
        e.preventDefault();
        fat.dispatchEvent(new Event('mousedown'));
      }, { passive: false });
      
      container.appendChild(fat);
      
      // Cleanup if missed
      setTimeout(() => {
        if (fat.parentElement) fat.remove();
      }, 5000);
    }
    
    miniGameLoopId = requestAnimationFrame(spawnFat);
  };
  
  if (miniGameLoopId) cancelAnimationFrame(miniGameLoopId);
  miniGameLoopId = requestAnimationFrame(spawnFat);
}

const cursorController = (() => {
  const interactiveSelector = [
    'button',
    'a',
    'input',
    'select',
    'textarea',
    'label',
    '[role="button"]',
    '[data-action]',
    '.chip',
    '.checkbox-card',
    '.panel',
    '.day-card',
    '.dev-profile',
    '.fat-enemy',
  ].join(',');

  const pointer = {
    x: window.innerWidth / 2,
    y: window.innerHeight / 2,
    renderedX: window.innerWidth / 2,
    renderedY: window.innerHeight / 2,
    magneticX: 0,
    magneticY: 0,
  };

  let mode = null;
  let node = null;
  let rafId = null;
  let bound = false;
  let isInteractive = false;
  let isVisible = false;

  const canUseCustomCursor = () => window.matchMedia('(pointer: fine)').matches;

  const template = (nextMode) => nextMode === 'loading_scope_cursor'
    ? '<span class="scope-ring"></span><span class="scope-cross scope-cross-x"></span><span class="scope-cross scope-cross-y"></span><span class="scope-dot"></span><span class="scope-orbit"></span>'
    : '<span class="macos-arrow"></span>';

  const cleanupScopeEffects = () => {
    document.querySelectorAll('.scope-shot-trail, .scope-shot-ping').forEach((effect) => effect.remove());
  };

  const ensureNode = () => {
    if (node && node.isConnected) return node;
    node = document.createElement('div');
    node.id = 'global-cursor';
    node.className = 'global-cursor';
    node.setAttribute('aria-hidden', 'true');
    document.body.appendChild(node);
    return node;
  };

  const setModeClass = (nextMode) => {
    document.body.classList.remove('cursor-mode-loading_scope_cursor', 'cursor-mode-native_macos_cursor');
    document.body.classList.add(`cursor-mode-${nextMode}`);
  };

  const setInteractive = (value) => {
    isInteractive = value;
    if (node) node.classList.toggle('is-interactive', value);
  };

  const animate = () => {
    if (!node || !isVisible) {
      rafId = null;
      return;
    }

    const lag = mode === 'loading_scope_cursor' ? 0.22 : 0.34;
    const magneticEase = mode === 'native_macos_cursor' && isInteractive ? 0.16 : 0.26;
    pointer.renderedX += (pointer.x + pointer.magneticX - pointer.renderedX) * lag;
    pointer.renderedY += (pointer.y + pointer.magneticY - pointer.renderedY) * lag;
    pointer.magneticX += (0 - pointer.magneticX) * magneticEase;
    pointer.magneticY += (0 - pointer.magneticY) * magneticEase;
    node.style.transform = `translate3d(${pointer.renderedX}px, ${pointer.renderedY}px, 0)`;
    rafId = requestAnimationFrame(animate);
  };

  const startAnimation = () => {
    if (!rafId) rafId = requestAnimationFrame(animate);
  };

  const destroyNode = () => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    isVisible = false;
    node?.remove();
    node = null;
    document.body.classList.remove('cursor-mode-loading_scope_cursor', 'cursor-mode-native_macos_cursor');
    cleanupScopeEffects();
  };

  const bindGlobalEvents = () => {
    if (bound) return;
    bound = true;

    window.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'touch') return;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      isVisible = true;

      const target = event.target instanceof Element ? event.target : null;
      const interactive = Boolean(target?.closest(interactiveSelector));
      setInteractive(interactive);

      if (mode === 'native_macos_cursor' && interactive) {
        const magnetTarget = target.closest(interactiveSelector);
        const rect = magnetTarget?.getBoundingClientRect();
        if (rect) {
          pointer.magneticX = Math.max(-4, Math.min(4, (rect.left + rect.width / 2 - event.clientX) * 0.055));
          pointer.magneticY = Math.max(-4, Math.min(4, (rect.top + rect.height / 2 - event.clientY) * 0.055));
        }
      }

      startAnimation();
    }, { passive: true });

    window.addEventListener('pointerdown', (event) => {
      if (event.pointerType === 'touch' || !node) return;
      node.classList.remove('is-pressing');
      node.getBoundingClientRect();
      node.classList.add('is-pressing');
    }, { passive: true });

    window.addEventListener('pointerup', () => {
      node?.classList.remove('is-pressing');
    }, { passive: true });

    document.addEventListener('pointerleave', () => {
      if (node) node.classList.add('is-hidden');
    });

    document.addEventListener('pointerenter', () => {
      if (node) node.classList.remove('is-hidden');
    });

    window.addEventListener('resize', () => {
      pointer.x = Math.min(pointer.x, window.innerWidth);
      pointer.y = Math.min(pointer.y, window.innerHeight);
    }, { passive: true });
  };

  const sync = (nextMode) => {
    const customCursorAllowed = canUseCustomCursor();
    if (!customCursorAllowed) {
      destroyNode();
      mode = nextMode;
      return;
    }

    bindGlobalEvents();

    if (mode !== nextMode) {
      if (mode === 'loading_scope_cursor' && nextMode !== 'loading_scope_cursor') {
        cleanupScopeEffects();
      }
      mode = nextMode;
      const cursorNode = ensureNode();
      cursorNode.className = `global-cursor ${nextMode}`;
      cursorNode.innerHTML = template(nextMode);
      setModeClass(nextMode);
      setInteractive(false);
    } else {
      ensureNode();
      setModeClass(nextMode);
    }

    isVisible = true;
    startAnimation();
  };

  const getPointer = () => ({ x: pointer.x, y: pointer.y, mode });

  return { sync, getPointer };
})();

function createScopeShotEffect(x, y, options = {}) {
  const { mode, x: pointerX, y: pointerY } = cursorController.getPointer();
  if (mode !== 'loading_scope_cursor') return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const originX = Number.isFinite(options.originX) ? options.originX : pointerX;
  const originY = Number.isFinite(options.originY) ? options.originY : pointerY;
  const dx = x - originX;
  const dy = y - originY;
  const length = Math.max(18, Math.hypot(dx, dy));
  const angle = Math.atan2(dy, dx);

  const ping = document.createElement('span');
  ping.className = 'scope-shot-ping';
  ping.style.left = `${x}px`;
  ping.style.top = `${y}px`;
  document.body.appendChild(ping);

  if (!reduceMotion) {
    const trail = document.createElement('span');
    trail.className = 'scope-shot-trail';
    trail.style.left = `${originX}px`;
    trail.style.top = `${originY}px`;
    trail.style.width = `${Math.min(length, window.innerWidth * 0.82)}px`;
    trail.style.transform = `rotate(${angle}rad)`;
    document.body.appendChild(trail);
    window.setTimeout(() => trail.remove(), 240);
  }

  window.setTimeout(() => ping.remove(), reduceMotion ? 100 : 300);
}

function bindMiniGame() {
  const container = document.getElementById('mini-game-container');
  if (!container) return;

  let score = 0;
  let spawnRate = window.matchMedia('(max-width: 680px)').matches ? 1350 : 1150;
  let lastSpawn = 0;
  const hazards = ['BAD', 'SUGAR', 'FRY', 'OIL', 'JUNK'];
  const bursts = ['OK', '+', 'FIT', 'AI'];
  const scoreBoard = document.getElementById('game-score');

  const fireFrom = (event) => {
    const isTouch = event.pointerType === 'touch';
    const pointer = cursorController.getPointer();
    createScopeShotEffect(event.clientX, event.clientY, {
      pointerType: event.pointerType,
      originX: isTouch ? window.innerWidth / 2 : pointer.x,
      originY: isTouch ? window.innerHeight - 34 : pointer.y,
    });
  };

  const hitEnemy = (enemy, event) => {
    if (!enemy || !enemy.parentElement) return;

    score += 1;
    if (scoreBoard) scoreBoard.innerText = score;

    const rect = enemy.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    enemy.remove();

    for (let i = 0; i < 4; i += 1) {
      const burst = document.createElement('div');
      burst.className = 'veggie-burst';
      burst.innerText = bursts[Math.floor(Math.random() * bursts.length)];
      burst.style.left = `${centerX}px`;
      burst.style.top = `${centerY}px`;
      burst.style.setProperty('--tx', `${Math.random() * 150 - 75}px`);
      burst.style.setProperty('--ty', `${Math.random() * -115 - 35}px`);
      document.body.appendChild(burst);
      window.setTimeout(() => burst.remove(), 760);
    }

    fireFrom(event);
  };

  container.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    const enemy = event.target.closest('.fat-enemy');
    if (enemy) hitEnemy(enemy, event);
    else fireFrom(event);
  });

  const spawnFat = (now) => {
    if (state.page !== 'generating') {
      if (miniGameLoopId) cancelAnimationFrame(miniGameLoopId);
      return;
    }

    if (now - lastSpawn > spawnRate) {
      lastSpawn = now;
      spawnRate = Math.max(window.innerWidth < 680 ? 620 : 420, spawnRate - 45);

      const fat = document.createElement('div');
      fat.className = 'fat-enemy';
      fat.innerText = hazards[Math.floor(Math.random() * hazards.length)];
      fat.style.left = `${Math.random() * 78 + 8}%`;
      fat.style.animationDuration = `${Math.random() * 1.5 + (window.innerWidth < 680 ? 3.4 : 2.7)}s`;
      container.appendChild(fat);

      window.setTimeout(() => {
        if (fat.parentElement) fat.remove();
      }, 5000);
    }

    miniGameLoopId = requestAnimationFrame(spawnFat);
  };

  if (miniGameLoopId) cancelAnimationFrame(miniGameLoopId);
  miniGameLoopId = requestAnimationFrame(spawnFat);
}

await loadTranslations();
render();
