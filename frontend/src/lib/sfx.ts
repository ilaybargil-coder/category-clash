const MUTE_STORAGE_KEY = "cc_mute";
const SILENCE = 0.0001;

let audioContext: AudioContext | null = null;
let mutePreferenceLoaded = false;

/** Shared mute state. Prefer isMuted() so the persisted preference is loaded first. */
export let muted = false;

function loadMutePreference() {
  if (mutePreferenceLoaded) return;
  mutePreferenceLoaded = true;

  try {
    if (typeof window !== "undefined") {
      muted = window.localStorage.getItem(MUTE_STORAGE_KEY) === "true";
    }
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }
}

export function isMuted(): boolean {
  loadMutePreference();
  return muted;
}

export function toggleMute(): boolean {
  try {
    muted = !isMuted();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(MUTE_STORAGE_KEY, String(muted));
    }
  } catch {
    // Keep the in-memory preference even when persistence is unavailable.
  }
  return muted;
}

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;

  if (!audioContext) {
    const AudioContextConstructor =
      window.AudioContext ??
      (window as Window & { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!AudioContextConstructor) return null;
    audioContext = new AudioContextConstructor();
  }

  if (audioContext.state === "suspended") {
    void audioContext.resume().catch(() => undefined);
  }
  return audioContext;
}

function tone(
  context: AudioContext,
  start: number,
  duration: number,
  frequency: number,
  volume: number,
  type: OscillatorType = "sine"
) {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  const attackEnd = start + Math.min(0.008, duration / 4);
  const end = start + duration;

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(SILENCE, start);
  gain.gain.linearRampToValueAtTime(volume, attackEnd);
  gain.gain.exponentialRampToValueAtTime(SILENCE, end);

  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(start);
  oscillator.stop(end + 0.01);
}

function withAudio(render: (context: AudioContext, now: number) => void) {
  try {
    if (isMuted()) return;
    const context = getAudioContext();
    if (!context) return;
    render(context, context.currentTime + 0.005);
  } catch {
    // Sound effects should never interrupt gameplay.
  }
}

export function playAccept() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.075, 600, 0.035);
      tone(context, now + 0.075, 0.075, 900, 0.04);
    });
  } catch {}
}

export function playReject() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.2, 180, 0.022, "sawtooth");
    });
  } catch {}
}

export function playDuplicate() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.1, 440, 0.025);
    });
  } catch {}
}

export function playTick() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.08, 800, 0.012);
    });
  } catch {}
}

export function playRoundWin() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.16, 523, 0.03);
      tone(context, now + 0.12, 0.16, 659, 0.034);
      tone(context, now + 0.24, 0.16, 784, 0.038);
    });
  } catch {}
}

export function playRoundLoss() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.17, 392, 0.026);
      tone(context, now + 0.13, 0.17, 294, 0.022);
    });
  } catch {}
}

export function playMatchWin() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.15, 523, 0.032);
      tone(context, now + 0.12, 0.15, 659, 0.034);
      tone(context, now + 0.24, 0.15, 784, 0.037);
      tone(context, now + 0.36, 0.15, 1047, 0.04);
    });
  } catch {}
}

export function playMatchLoss() {
  try {
    withAudio((context, now) => {
      tone(context, now, 0.19, 330, 0.026);
      tone(context, now + 0.16, 0.19, 220, 0.021);
    });
  } catch {}
}
