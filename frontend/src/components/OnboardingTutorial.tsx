"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  GamepadIcon,
  JokerIcon,
  SwapIcon,
  TargetIcon,
  TimerIcon,
  TrophyIcon,
} from "@/components/icons";

const ONBOARDING_STORAGE_KEY = "cc_onboarding_seen";
const SWIPE_THRESHOLD = 48;

const slides = [
  {
    title: "קרב קטגוריות",
    eyebrow: "ברוכים הבאים",
    icon: GamepadIcon,
    content: (
      <p className="text-base leading-7 text-slate-300 sm:text-lg sm:leading-8">
        קרב קטגוריות הוא משחק בזמן אמת: כותבים כמה שיותר תשובות נכונות
        לפני שהזמן נגמר ומנסים לגבור על היריב.
      </p>
    ),
  },
  {
    title: "איך סיבוב עובד?",
    eyebrow: "פשוט מתחילים לענות",
    icon: TargetIcon,
    content: (
      <div className="space-y-3 text-sm leading-6 text-slate-300 sm:text-base">
        <p>מקבלים קטגוריה ומקלידים תשובות שמתאימות לה.</p>
        <p>
          מנגנון ההתאמה הסלחני מקבל גם וריאציות כתיב, אז לא צריך להיתקע על
          אות קטנה.
        </p>
        <p>אתם והיריב עונים בתורות — שמרו על רצף עד שהזמן נגמר.</p>
      </div>
    ),
  },
  {
    title: "כוחות מיוחדים",
    eyebrow: "השתמשו בהם בחוכמה",
    icon: TimerIcon,
    content: (
      <ul className="space-y-3 text-right">
        <li className="flex items-center gap-3 rounded-xl border border-white/10 bg-slate-950/25 p-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-violet-500/15 text-violet-300">
            <SwapIcon size={22} />
          </span>
          <span>
            <strong className="block text-white">החלפה</strong>
            <span className="text-sm text-slate-400">מחליפים את השאלה בקטגוריה חדשה.</span>
          </span>
        </li>
        <li className="flex items-center gap-3 rounded-xl border border-white/10 bg-slate-950/25 p-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-emerald-500/15 text-emerald-300">
            <TimerIcon size={22} />
          </span>
          <span>
            <strong className="block text-white">הארכה</strong>
            <span className="text-sm text-slate-400">מוסיפים עוד זמן לסיבוב.</span>
          </span>
        </li>
        <li className="flex items-center gap-3 rounded-xl border border-white/10 bg-slate-950/25 p-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-amber-500/15 text-amber-300">
            <JokerIcon size={22} />
          </span>
          <span>
            <strong className="block text-white">ג&apos;וקר</strong>
            <span className="text-sm text-slate-400">מקבלים עזרה כשצריך תשובה טובה.</span>
          </span>
        </li>
      </ul>
    ),
  },
  {
    title: "בחרו איך לשחק",
    eyebrow: "תמיד יש עוד אתגר",
    icon: TrophyIcon,
    content: (
      <div className="space-y-3 text-sm leading-6 text-slate-300 sm:text-base">
        <p>
          <strong className="text-white">1v1 מול חברים</strong> — קרב ראש בראש
          בזמן אמת.
        </p>
        <p>
          <strong className="text-white">אתגר יומי</strong> — אותה קטגוריה
          לכולם, בכל יום.
        </p>
        <p>
          <strong className="text-white">אימון</strong> — מתרגלים לבד ובקצב
          שלכם.
        </p>
        <p className="rounded-xl border border-violet-400/20 bg-violet-500/10 p-3 text-violet-100">
          בכל מצב צוברים XP, עולים רמות וממשיכים להשתפר.
        </p>
      </div>
    ),
  },
];

export default function OnboardingTutorial() {
  const [isVisible, setIsVisible] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);
  const touchStartX = useRef<number | null>(null);
  const isLastSlide = currentSlide === slides.length - 1;

  useEffect(() => {
    if (typeof window === "undefined") return;

    const checkStorage = window.setTimeout(() => {
      try {
        setIsVisible(window.localStorage.getItem(ONBOARDING_STORAGE_KEY) === null);
      } catch {
        setIsVisible(true);
      }
    }, 0);

    return () => window.clearTimeout(checkStorage);
  }, []);

  const finishOnboarding = useCallback(() => {
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(ONBOARDING_STORAGE_KEY, "true");
      } catch {
        // The tutorial should still close if storage is unavailable.
      }
    }

    setIsVisible(false);
  }, []);

  const goForward = useCallback(() => {
    if (currentSlide === slides.length - 1) {
      finishOnboarding();
      return;
    }

    setCurrentSlide((slide) => slide + 1);
  }, [currentSlide, finishOnboarding]);

  useEffect(() => {
    if (!isVisible || typeof window === "undefined") return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        goForward();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goForward, isVisible]);

  if (typeof window === "undefined" || !isVisible) return null;

  const slide = slides[currentSlide];
  const SlideIcon = slide.icon;

  const handleTouchEnd = (event: React.TouchEvent<HTMLDivElement>) => {
    if (touchStartX.current === null) return;

    const distance = event.changedTouches[0].clientX - touchStartX.current;
    touchStartX.current = null;

    if (Math.abs(distance) < SWIPE_THRESHOLD) return;

    if (distance < 0 && currentSlide > 0) {
      setCurrentSlide((index) => index - 1);
    } else if (distance > 0) {
      goForward();
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-[#090713]/90 p-4 backdrop-blur-md sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      dir="rtl"
    >
      <div
        className="surface-panel relative my-auto w-full max-w-lg overflow-hidden rounded-3xl p-5 shadow-2xl sm:p-8"
        onTouchStart={(event) => {
          touchStartX.current = event.touches[0].clientX;
        }}
        onTouchEnd={handleTouchEnd}
      >
        <div className="pointer-events-none absolute -right-24 -top-24 h-56 w-56 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 -left-20 h-56 w-56 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative flex items-center justify-between">
          <span className="text-xs font-bold tracking-wide text-slate-500">
            {currentSlide + 1} / {slides.length}
          </span>
          <button
            type="button"
            onClick={finishOnboarding}
            className="rounded-lg px-2 py-1 text-sm font-bold text-slate-400 transition-colors hover:bg-white/5 hover:text-white focus:outline-none focus:ring-2 focus:ring-violet-400"
          >
            דלג
          </button>
        </div>

        <div key={currentSlide} className="relative mt-5 animate-pop-in text-center">
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl border border-violet-300/20 bg-violet-500/15 text-violet-300 shadow-lg shadow-violet-950/30 sm:h-20 sm:w-20">
            <SlideIcon className="h-9 w-9 sm:h-11 sm:w-11" />
          </div>
          <p className="mt-5 text-xs font-black uppercase tracking-[0.18em] text-violet-300">
            {slide.eyebrow}
          </p>
          <h2 id="onboarding-title" className="mt-2 text-2xl font-black text-white sm:text-3xl">
            {slide.title}
          </h2>
          <div className="mt-5 min-h-[12rem] text-right sm:min-h-[13rem]">
            {slide.content}
          </div>
        </div>

        <div className="relative mt-5 flex items-center justify-center gap-2" aria-label="שלבי ההדרכה">
          {slides.map((item, index) => (
            <button
              key={item.title}
              type="button"
              onClick={() => setCurrentSlide(index)}
              className={`h-2.5 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                index === currentSlide
                  ? "w-7 bg-violet-400"
                  : "w-2.5 bg-slate-600 hover:bg-slate-500"
              }`}
              aria-label={`מעבר לשלב ${index + 1}`}
              aria-current={index === currentSlide ? "step" : undefined}
            />
          ))}
        </div>

        <div className="relative mt-6 flex gap-3">
          {currentSlide > 0 && (
            <button
              type="button"
              onClick={() => setCurrentSlide((slideIndex) => slideIndex - 1)}
              className="secondary-button px-5"
            >
              הקודם
            </button>
          )}
          <button
            type="button"
            onClick={goForward}
            className="primary-button flex-1 px-6 py-3.5 text-base"
          >
            {isLastSlide ? "בואו נתחיל" : "הבא ←"}
          </button>
        </div>

        <p className="relative mt-3 text-center text-[11px] text-slate-500">
          אפשר גם ללחוץ Enter כדי להמשיך
        </p>
      </div>
    </div>
  );
}
