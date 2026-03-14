"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./SoundDesigner.module.css";

type DesignerTab = "custom" | "presets";

type VoiceDesignTemplate = {
  text?: string;
  language?: string;
  voice_profile?: {
    identity?: {
      gender_presentation?: string;
      age_impression?: string;
      accent_pronunciation?: string;
    };
    voice_body?: {
      pitch?: string;
      vocal_weight?: string;
      roughness_grit?: string;
    };
    delivery?: {
      speaking_pace?: string;
      energy_level?: string;
      dramatic_pause_intensity?: string;
    };
    personality?: {
      emotional_tone?: string[];
      authority_dominance?: string;
      warmth_coldness?: string;
    };
  };
  generation_options?: {
    max_new_tokens?: number;
    output_format?: string;
    sample_rate?: number;
    return_base64?: boolean;
  };
};

type VoicePreset = {
  preset_name: string;
  display_name: string;
  description: string;
  request_template?: VoiceDesignTemplate;
  response_payload?: Record<string, unknown>;
};

type PresetsResponse = {
  success?: boolean;
  presets?: VoicePreset[];
  message?: string;
};

type PresetResponse = {
  success?: boolean;
  preset?: VoicePreset;
  message?: string;
};

const API_BASE_ENV = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

const resolveApiBase = () => {
  if (API_BASE_ENV) {
    return API_BASE_ENV;
  }
  return "http://127.0.0.1:8000";
};

const GENDER_OPTIONS = ["masculine", "feminine", "neutral"] as const;
const AGE_OPTIONS = ["teen", "young", "mature", "elder"] as const;
const ACCENT_OPTIONS = ["neutral_english", "american_english", "british_english"] as const;

const PITCH_OPTIONS = ["very_low", "low", "mid", "high"] as const;
const VOCAL_WEIGHT_OPTIONS = ["light", "medium", "heavy", "very_heavy"] as const;
const ROUGHNESS_OPTIONS = ["smooth", "slight", "rough", "gritty"] as const;

const PACE_OPTIONS = ["very_slow", "slow", "medium", "fast"] as const;
const ENERGY_OPTIONS = ["calm", "controlled", "intense", "explosive"] as const;
const PAUSE_OPTIONS = ["minimal", "natural", "strong", "cinematic"] as const;

const EMOTIONAL_TONE_OPTIONS = ["serious", "inspirational", "aggressive"] as const;
const AUTHORITY_OPTIONS = ["soft", "balanced", "dominant", "commanding"] as const;
const WARMTH_OPTIONS = ["cold", "slight_cold", "balanced", "warm"] as const;

const LANGUAGE_OPTIONS = ["en", "zh", "ar", "ur"] as const;
const OUTPUT_FORMAT_OPTIONS = ["wav", "mp3"] as const;
const SAMPLE_RATE_OPTIONS = [16000, 22050, 24000, 44100] as const;

const DEFAULT_TEXT =
  "Excuses are the language of weak discipline. Get up and prove your worth.";

const includesValue = <T extends string | number>(
  options: readonly T[],
  value: unknown
): value is T => options.includes(value as T);

const toLabel = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());

const prettyJson = (value: unknown) => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const showApiPopup = (title: string, payload: unknown) => {
  if (typeof window === "undefined") {
    return;
  }
  window.alert(`${title}\n\n${prettyJson(payload)}`);
};

const parseJsonSafely = async <T,>(response: Response): Promise<T | null> => {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
};

const getFetchErrorMessage = (error: unknown, apiBase: string, action: string) => {
  if (error instanceof TypeError) {
    return `Network error while ${action}. Unable to reach API at ${apiBase}.`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return `Unable to ${action}.`;
};

type CustomDesignerTabProps = {
  text: string;
  language: (typeof LANGUAGE_OPTIONS)[number];
  genderPresentation: (typeof GENDER_OPTIONS)[number];
  ageImpression: (typeof AGE_OPTIONS)[number];
  accentPronunciation: (typeof ACCENT_OPTIONS)[number];
  pitch: (typeof PITCH_OPTIONS)[number];
  vocalWeight: (typeof VOCAL_WEIGHT_OPTIONS)[number];
  roughnessGrit: (typeof ROUGHNESS_OPTIONS)[number];
  speakingPace: (typeof PACE_OPTIONS)[number];
  energyLevel: (typeof ENERGY_OPTIONS)[number];
  dramaticPauseIntensity: (typeof PAUSE_OPTIONS)[number];
  emotionalTone: string[];
  authorityDominance: (typeof AUTHORITY_OPTIONS)[number];
  warmthColdness: (typeof WARMTH_OPTIONS)[number];
  maxNewTokens: number;
  outputFormat: (typeof OUTPUT_FORMAT_OPTIONS)[number];
  sampleRate: (typeof SAMPLE_RATE_OPTIONS)[number];
  returnBase64: boolean;
  isGenerating: boolean;
  onTextChange: (value: string) => void;
  onLanguageChange: (value: (typeof LANGUAGE_OPTIONS)[number]) => void;
  onGenderChange: (value: (typeof GENDER_OPTIONS)[number]) => void;
  onAgeChange: (value: (typeof AGE_OPTIONS)[number]) => void;
  onAccentChange: (value: (typeof ACCENT_OPTIONS)[number]) => void;
  onPitchChange: (value: (typeof PITCH_OPTIONS)[number]) => void;
  onVocalWeightChange: (value: (typeof VOCAL_WEIGHT_OPTIONS)[number]) => void;
  onRoughnessChange: (value: (typeof ROUGHNESS_OPTIONS)[number]) => void;
  onPaceChange: (value: (typeof PACE_OPTIONS)[number]) => void;
  onEnergyChange: (value: (typeof ENERGY_OPTIONS)[number]) => void;
  onPauseChange: (value: (typeof PAUSE_OPTIONS)[number]) => void;
  onToggleTone: (value: (typeof EMOTIONAL_TONE_OPTIONS)[number]) => void;
  onAuthorityChange: (value: (typeof AUTHORITY_OPTIONS)[number]) => void;
  onWarmthChange: (value: (typeof WARMTH_OPTIONS)[number]) => void;
  onMaxNewTokensChange: (value: number) => void;
  onOutputFormatChange: (value: (typeof OUTPUT_FORMAT_OPTIONS)[number]) => void;
  onSampleRateChange: (value: (typeof SAMPLE_RATE_OPTIONS)[number]) => void;
  onReturnBase64Change: (value: boolean) => void;
  onGenerate: () => void;
};

function CustomDesignerTab({
  text,
  language,
  genderPresentation,
  ageImpression,
  accentPronunciation,
  pitch,
  vocalWeight,
  roughnessGrit,
  speakingPace,
  energyLevel,
  dramaticPauseIntensity,
  emotionalTone,
  authorityDominance,
  warmthColdness,
  maxNewTokens,
  outputFormat,
  sampleRate,
  returnBase64,
  isGenerating,
  onTextChange,
  onLanguageChange,
  onGenderChange,
  onAgeChange,
  onAccentChange,
  onPitchChange,
  onVocalWeightChange,
  onRoughnessChange,
  onPaceChange,
  onEnergyChange,
  onPauseChange,
  onToggleTone,
  onAuthorityChange,
  onWarmthChange,
  onMaxNewTokensChange,
  onOutputFormatChange,
  onSampleRateChange,
  onReturnBase64Change,
  onGenerate,
}: CustomDesignerTabProps) {
  return (
    <section
      aria-labelledby="sound-designer-custom-tab"
      className={styles.contentWrap}
      id="sound-designer-custom"
      role="tabpanel"
    >
      <div className={styles.designerGrid}>
        <div className={styles.leftColumn}>
          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 1 - Identity</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Gender Presentation</p>
                <div className={styles.pillRow}>
                  {GENDER_OPTIONS.map((option) => (
                    <button
                      className={`${styles.pillButton} ${
                        genderPresentation === option ? styles.pillButtonActive : ""
                      }`}
                      key={option}
                      onClick={() => onGenderChange(option)}
                      type="button"
                    >
                      {toLabel(option)}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Age Impression</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) => onAgeChange(event.target.value as (typeof AGE_OPTIONS)[number])}
                  value={ageImpression}
                >
                  {AGE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Accent / Pronunciation</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) =>
                    onAccentChange(event.target.value as (typeof ACCENT_OPTIONS)[number])
                  }
                  value={accentPronunciation}
                >
                  {ACCENT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 2 - Voice Body</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Pitch</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) => onPitchChange(event.target.value as (typeof PITCH_OPTIONS)[number])}
                  value={pitch}
                >
                  {PITCH_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Vocal Weight</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) =>
                    onVocalWeightChange(event.target.value as (typeof VOCAL_WEIGHT_OPTIONS)[number])
                  }
                  value={vocalWeight}
                >
                  {VOCAL_WEIGHT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Roughness / Grit</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) =>
                    onRoughnessChange(event.target.value as (typeof ROUGHNESS_OPTIONS)[number])
                  }
                  value={roughnessGrit}
                >
                  {ROUGHNESS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 3 - Delivery</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Speaking Pace</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) => onPaceChange(event.target.value as (typeof PACE_OPTIONS)[number])}
                  value={speakingPace}
                >
                  {PACE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Energy Level</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) => onEnergyChange(event.target.value as (typeof ENERGY_OPTIONS)[number])}
                  value={energyLevel}
                >
                  {ENERGY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Dramatic Pause Intensity</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) => onPauseChange(event.target.value as (typeof PAUSE_OPTIONS)[number])}
                  value={dramaticPauseIntensity}
                >
                  {PAUSE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 4 - Personality</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Emotional Tone</p>
                <div className={styles.pillRow}>
                  {EMOTIONAL_TONE_OPTIONS.map((option) => (
                    <button
                      className={`${styles.pillButton} ${
                        emotionalTone.includes(option) ? styles.pillButtonActive : ""
                      }`}
                      key={option}
                      onClick={() => onToggleTone(option)}
                      type="button"
                    >
                      {toLabel(option)}
                    </button>
                  ))}
                </div>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Authority / Dominance</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) =>
                    onAuthorityChange(event.target.value as (typeof AUTHORITY_OPTIONS)[number])
                  }
                  value={authorityDominance}
                >
                  {AUTHORITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Warmth vs Coldness</p>
                <select
                  className={styles.selectMock}
                  onChange={(event) => onWarmthChange(event.target.value as (typeof WARMTH_OPTIONS)[number])}
                  value={warmthColdness}
                >
                  {WARMTH_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </section>
        </div>

        <div className={styles.rightColumn}>
          <section className={styles.sideCard}>
            <h2 className={styles.sideHeading}>Text Input</h2>
            <div className={styles.sideBody}>
              <label className={styles.fieldLabel}>
                Text
                <textarea
                  className={styles.textareaInput}
                  onChange={(event) => onTextChange(event.target.value)}
                  rows={6}
                  value={text}
                />
              </label>
              <label className={styles.fieldLabel}>
                Language
                <select
                  className={styles.selectMock}
                  onChange={(event) =>
                    onLanguageChange(event.target.value as (typeof LANGUAGE_OPTIONS)[number])
                  }
                  value={language}
                >
                  {LANGUAGE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {toLabel(option)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className={styles.sideCard}>
            <h2 className={styles.sideHeading}>Voice Preview</h2>
            <div className={styles.previewStack}>
              <p className={styles.helperText}>Audio playback will be wired in the next step.</p>
            </div>
          </section>

          <section className={styles.sideCard}>
            <h2 className={styles.sideHeading}>Generate Voice</h2>
            <div className={styles.sideBody}>
              <label className={styles.fieldLabel}>
                Max New Tokens
                <input
                  className={styles.textInput}
                  min={1}
                  onChange={(event) => {
                    const nextValue = Number.parseInt(event.target.value, 10);
                    onMaxNewTokensChange(Number.isFinite(nextValue) ? nextValue : 1);
                  }}
                  type="number"
                  value={maxNewTokens}
                />
              </label>

              <label className={styles.fieldLabel}>
                Output Format
                <select
                  className={styles.selectMock}
                  onChange={(event) =>
                    onOutputFormatChange(event.target.value as (typeof OUTPUT_FORMAT_OPTIONS)[number])
                  }
                  value={outputFormat}
                >
                  {OUTPUT_FORMAT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option.toUpperCase()}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.fieldLabel}>
                Sample Rate
                <select
                  className={styles.selectMock}
                  onChange={(event) => onSampleRateChange(Number(event.target.value) as (typeof SAMPLE_RATE_OPTIONS)[number])}
                  value={sampleRate}
                >
                  {SAMPLE_RATE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.checkboxLabel}>
                <input
                  checked={returnBase64}
                  onChange={(event) => onReturnBase64Change(event.target.checked)}
                  type="checkbox"
                />
                Return Base64
              </label>

              <div className={styles.generateRow}>
                <button className={styles.generateButton} disabled={isGenerating} onClick={onGenerate} type="button">
                  {isGenerating ? "Generating..." : "Generate"}
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}

type VoicePresetsTabProps = {
  presets: VoicePreset[];
  isLoadingPresets: boolean;
  presetLoadError: string | null;
  applyingPresetId: string | null;
  onApplyPreset: (presetId: string) => void;
  onReload: () => void;
};

function VoicePresetsTab({
  presets,
  isLoadingPresets,
  presetLoadError,
  applyingPresetId,
  onApplyPreset,
  onReload,
}: VoicePresetsTabProps) {
  return (
    <section
      aria-labelledby="sound-designer-presets-tab"
      className={styles.contentWrap}
      id="sound-designer-presets"
      role="tabpanel"
    >
      <div className={styles.presetActionRow}>
        <button className={styles.applyButton} onClick={onReload} type="button">
          Reload Presets
        </button>
      </div>

      {isLoadingPresets ? <p className={styles.helperText}>Loading presets...</p> : null}
      {presetLoadError ? <p className={styles.errorMessage}>{presetLoadError}</p> : null}

      {!isLoadingPresets && !presetLoadError ? (
        <div className={styles.presetsList}>
          {presets.map((preset, index) => {
            const template = preset.request_template;
            const primaryValues = [
              template?.voice_profile?.identity?.gender_presentation,
              template?.voice_profile?.identity?.age_impression,
              template?.voice_profile?.voice_body?.pitch,
              template?.voice_profile?.voice_body?.vocal_weight,
              template?.voice_profile?.delivery?.speaking_pace,
              template?.voice_profile?.personality?.authority_dominance,
            ].filter((value): value is string => Boolean(value));

            const secondaryValues = [
              ...(template?.voice_profile?.personality?.emotional_tone ?? []),
              template?.voice_profile?.delivery?.dramatic_pause_intensity,
              template?.voice_profile?.personality?.warmth_coldness,
            ].filter((value): value is string => Boolean(value));

            return (
              <article className={styles.presetCard} key={preset.preset_name}>
                <h2 className={styles.presetTitle}>
                  {index + 1}. {preset.display_name} ({preset.preset_name})
                </h2>
                <div className={styles.presetBody}>
                  <div className={styles.presetLines}>
                    <p className={styles.presetLine}>{preset.description}</p>
                    {primaryValues.length ? (
                      <p className={styles.presetLine}>{primaryValues.map(toLabel).join(" | ")}</p>
                    ) : null}
                    {secondaryValues.length ? (
                      <p className={styles.presetLine}>{secondaryValues.map(toLabel).join(" | ")}</p>
                    ) : null}
                  </div>
                  <button
                    className={styles.applyButton}
                    disabled={applyingPresetId === preset.preset_name}
                    onClick={() => onApplyPreset(preset.preset_name)}
                    type="button"
                  >
                    {applyingPresetId === preset.preset_name ? "Applying..." : "Apply"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export default function SoundDesigner() {
  const router = useRouter();
  const apiBase = useMemo(resolveApiBase, []);

  const [activeTab, setActiveTab] = useState<DesignerTab>("custom");

  const [text, setText] = useState(DEFAULT_TEXT);
  const [language, setLanguage] = useState<(typeof LANGUAGE_OPTIONS)[number]>("en");

  const [genderPresentation, setGenderPresentation] = useState<(typeof GENDER_OPTIONS)[number]>("masculine");
  const [ageImpression, setAgeImpression] = useState<(typeof AGE_OPTIONS)[number]>("young");
  const [accentPronunciation, setAccentPronunciation] = useState<(typeof ACCENT_OPTIONS)[number]>("neutral_english");

  const [pitch, setPitch] = useState<(typeof PITCH_OPTIONS)[number]>("low");
  const [vocalWeight, setVocalWeight] = useState<(typeof VOCAL_WEIGHT_OPTIONS)[number]>("heavy");
  const [roughnessGrit, setRoughnessGrit] = useState<(typeof ROUGHNESS_OPTIONS)[number]>("rough");

  const [speakingPace, setSpeakingPace] = useState<(typeof PACE_OPTIONS)[number]>("medium");
  const [energyLevel, setEnergyLevel] = useState<(typeof ENERGY_OPTIONS)[number]>("intense");
  const [dramaticPauseIntensity, setDramaticPauseIntensity] = useState<(typeof PAUSE_OPTIONS)[number]>("strong");

  const [emotionalTone, setEmotionalTone] = useState<string[]>(["aggressive", "inspirational"]);
  const [authorityDominance, setAuthorityDominance] = useState<(typeof AUTHORITY_OPTIONS)[number]>("commanding");
  const [warmthColdness, setWarmthColdness] = useState<(typeof WARMTH_OPTIONS)[number]>("slight_cold");

  const [maxNewTokens, setMaxNewTokens] = useState(2048);
  const [outputFormat, setOutputFormat] = useState<(typeof OUTPUT_FORMAT_OPTIONS)[number]>("wav");
  const [sampleRate, setSampleRate] = useState<(typeof SAMPLE_RATE_OPTIONS)[number]>(24000);
  const [returnBase64, setReturnBase64] = useState(false);

  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [isLoadingPresets, setIsLoadingPresets] = useState(false);
  const [presetLoadError, setPresetLoadError] = useState<string | null>(null);
  const [applyingPresetId, setApplyingPresetId] = useState<string | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);

  const [latestResponse, setLatestResponse] = useState<unknown>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const applyTemplateToState = useCallback((template: VoiceDesignTemplate) => {
    if (typeof template.text === "string") {
      setText(template.text);
    }

    if (includesValue(LANGUAGE_OPTIONS, template.language)) {
      setLanguage(template.language);
    }

    const identity = template.voice_profile?.identity;
    if (includesValue(GENDER_OPTIONS, identity?.gender_presentation)) {
      setGenderPresentation(identity.gender_presentation);
    }
    if (includesValue(AGE_OPTIONS, identity?.age_impression)) {
      setAgeImpression(identity.age_impression);
    }
    if (includesValue(ACCENT_OPTIONS, identity?.accent_pronunciation)) {
      setAccentPronunciation(identity.accent_pronunciation);
    }

    const voiceBody = template.voice_profile?.voice_body;
    if (includesValue(PITCH_OPTIONS, voiceBody?.pitch)) {
      setPitch(voiceBody.pitch);
    }
    if (includesValue(VOCAL_WEIGHT_OPTIONS, voiceBody?.vocal_weight)) {
      setVocalWeight(voiceBody.vocal_weight);
    }
    if (includesValue(ROUGHNESS_OPTIONS, voiceBody?.roughness_grit)) {
      setRoughnessGrit(voiceBody.roughness_grit);
    }

    const delivery = template.voice_profile?.delivery;
    if (includesValue(PACE_OPTIONS, delivery?.speaking_pace)) {
      setSpeakingPace(delivery.speaking_pace);
    }
    if (includesValue(ENERGY_OPTIONS, delivery?.energy_level)) {
      setEnergyLevel(delivery.energy_level);
    }
    if (includesValue(PAUSE_OPTIONS, delivery?.dramatic_pause_intensity)) {
      setDramaticPauseIntensity(delivery.dramatic_pause_intensity);
    }

    const personality = template.voice_profile?.personality;
    if (Array.isArray(personality?.emotional_tone)) {
      const filtered = personality.emotional_tone.filter((value) =>
        includesValue(EMOTIONAL_TONE_OPTIONS, value)
      );
      if (filtered.length) {
        setEmotionalTone(filtered);
      }
    }
    if (includesValue(AUTHORITY_OPTIONS, personality?.authority_dominance)) {
      setAuthorityDominance(personality.authority_dominance);
    }
    if (includesValue(WARMTH_OPTIONS, personality?.warmth_coldness)) {
      setWarmthColdness(personality.warmth_coldness);
    }

    const generation = template.generation_options;
    if (typeof generation?.max_new_tokens === "number" && generation.max_new_tokens >= 1) {
      setMaxNewTokens(Math.trunc(generation.max_new_tokens));
    }
    if (includesValue(OUTPUT_FORMAT_OPTIONS, generation?.output_format)) {
      setOutputFormat(generation.output_format);
    }
    if (includesValue(SAMPLE_RATE_OPTIONS, generation?.sample_rate)) {
      setSampleRate(generation.sample_rate);
    }
    if (typeof generation?.return_base64 === "boolean") {
      setReturnBase64(generation.return_base64);
    }
  }, []);

  const fetchPresets = useCallback(async () => {
    setIsLoadingPresets(true);
    setPresetLoadError(null);

    try {
      const response = await fetch(`${apiBase}/api/v1/voice-design/presets`, {
        cache: "no-store",
      });
      const data = await parseJsonSafely<PresetsResponse>(response);

      if (!response.ok || !data?.success || !Array.isArray(data.presets)) {
        setPresets([]);
        const fallbackMessage = `Unable to load presets (${response.status}).`;
        const message = data?.message ?? fallbackMessage;
        setPresetLoadError(message);
        return;
      }

      setPresets(data.presets);
    } catch (error) {
      setPresets([]);
      setPresetLoadError(getFetchErrorMessage(error, apiBase, "loading voice presets"));
    } finally {
      setIsLoadingPresets(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchPresets();
  }, [fetchPresets]);

  const toggleEmotionalTone = (tone: (typeof EMOTIONAL_TONE_OPTIONS)[number]) => {
    setEmotionalTone((current) => {
      if (current.includes(tone)) {
        const next = current.filter((item) => item !== tone);
        return next.length ? next : current;
      }
      return [...current, tone];
    });
  };

  const handleGenerate = async () => {
    setInfoMessage(null);

    const trimmedText = text.trim();
    if (!trimmedText) {
      const content = {
        success: false,
        error: {
          message: "Text is required.",
        },
      };
      setLatestResponse(content);
      showApiPopup("Voice Design - Validation Error", content);
      return;
    }

    if (!emotionalTone.length) {
      const content = {
        success: false,
        error: {
          message: "Select at least one emotional tone.",
        },
      };
      setLatestResponse(content);
      showApiPopup("Voice Design - Validation Error", content);
      return;
    }

    setIsGenerating(true);

    const payload = {
      text: trimmedText,
      language,
      voice_profile: {
        identity: {
          gender_presentation: genderPresentation,
          age_impression: ageImpression,
          accent_pronunciation: accentPronunciation,
        },
        voice_body: {
          pitch,
          vocal_weight: vocalWeight,
          roughness_grit: roughnessGrit,
        },
        delivery: {
          speaking_pace: speakingPace,
          energy_level: energyLevel,
          dramatic_pause_intensity: dramaticPauseIntensity,
        },
        personality: {
          emotional_tone: emotionalTone,
          authority_dominance: authorityDominance,
          warmth_coldness: warmthColdness,
        },
      },
      generation_options: {
        max_new_tokens: maxNewTokens,
        output_format: outputFormat,
        sample_rate: sampleRate,
        return_base64: returnBase64,
      },
    };

    try {
      const response = await fetch(`${apiBase}/api/v1/voice-design/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await parseJsonSafely<Record<string, unknown>>(response);
      const responseBody = data ?? {
        success: false,
        error: {
          message: `Unexpected empty response (${response.status}).`,
        },
      };

      setLatestResponse(responseBody);

      if (!response.ok) {
        showApiPopup("Voice Design - API Error", responseBody);
        return;
      }
      const requestId = typeof responseBody.request_id === "string"
        ? responseBody.request_id.trim()
        : "";
      if (!requestId) {
        const content = {
          success: false,
          error: {
            message: "Voice design response is missing request_id.",
          },
          voice_design: responseBody,
        };
        setLatestResponse(content);
        showApiPopup("Voice Design - Invalid Response", content);
        return;
      }

      const enqueueResponse = await fetch(`${apiBase}/enqueue/custom_voice_design`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ request_id: requestId }),
      });

      const enqueueData = await parseJsonSafely<Record<string, unknown>>(enqueueResponse);
      const enqueueBody = enqueueData ?? {
        success: false,
        error: {
          message: `Unexpected empty enqueue response (${enqueueResponse.status}).`,
        },
      };
      const combinedResponse = {
        voice_design: responseBody,
        enqueue: enqueueBody,
      };
      setLatestResponse(combinedResponse);

      if (!enqueueResponse.ok) {
        showApiPopup("Voice Design Created - Enqueue Failed", combinedResponse);
        setInfoMessage("Voice design created, but enqueue failed.");
        return;
      }

      showApiPopup("Voice Design Queued", combinedResponse);
      setInfoMessage("Voice design completed and queued for audio generation.");
      router.push(`/custom-voices?request_id=${encodeURIComponent(requestId)}`);
    } catch (error) {
      const content = {
        success: false,
        error: {
          message: getFetchErrorMessage(error, apiBase, "creating voice design"),
        },
      };
      setLatestResponse(content);
      showApiPopup("Voice Design - Network Error", content);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApplyPreset = async (presetId: string) => {
    setInfoMessage(null);
    setApplyingPresetId(presetId);

    try {
      const response = await fetch(
        `${apiBase}/api/v1/voice-design/presets/${encodeURIComponent(presetId)}`,
        {
          cache: "no-store",
        }
      );

      const data = await parseJsonSafely<PresetResponse>(response);
      const responseBody = data ?? {
        success: false,
        message: `Unexpected empty response (${response.status}).`,
      };

      setLatestResponse(responseBody);

      if (!response.ok || !data?.success) {
        showApiPopup("Voice Preset - API Error", responseBody);
        return;
      }

      if (data.preset?.request_template) {
        applyTemplateToState(data.preset.request_template);
      }

      showApiPopup("Voice Preset Applied", responseBody);
      setInfoMessage(`Preset applied: ${presetId}`);
      setActiveTab("custom");
    } catch (error) {
      const content = {
        success: false,
        error: {
          message: getFetchErrorMessage(error, apiBase, "applying voice preset"),
        },
      };
      setLatestResponse(content);
      showApiPopup("Voice Preset - Network Error", content);
    } finally {
      setApplyingPresetId(null);
    }
  };

  const title = useMemo(
    () => (activeTab === "custom" ? "VOICE DESIGNER" : "VOICE PRESETS"),
    [activeTab]
  );

  return (
    <div className="mx-auto flex w-full max-w-[1240px] flex-col gap-4">
      <section className={`neon-panel ${styles.surface}`}>
        <header className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          <div aria-label="Sound designer tabs" className={styles.tabBar} role="tablist">
            <button
              aria-controls="sound-designer-custom"
              aria-selected={activeTab === "custom"}
              className={`${styles.tabButton} ${activeTab === "custom" ? styles.tabButtonActive : ""}`}
              id="sound-designer-custom-tab"
              onClick={() => setActiveTab("custom")}
              role="tab"
              type="button"
            >
              Custom Designer
            </button>
            <button
              aria-controls="sound-designer-presets"
              aria-selected={activeTab === "presets"}
              className={`${styles.tabButton} ${activeTab === "presets" ? styles.tabButtonActive : ""}`}
              id="sound-designer-presets-tab"
              onClick={() => setActiveTab("presets")}
              role="tab"
              type="button"
            >
              Voice Presets
            </button>
          </div>
        </header>

        {activeTab === "custom" ? (
          <CustomDesignerTab
            ageImpression={ageImpression}
            authorityDominance={authorityDominance}
            dramaticPauseIntensity={dramaticPauseIntensity}
            emotionalTone={emotionalTone}
            energyLevel={energyLevel}
            genderPresentation={genderPresentation}
            isGenerating={isGenerating}
            language={language}
            maxNewTokens={maxNewTokens}
            onAccentChange={setAccentPronunciation}
            onAgeChange={setAgeImpression}
            onAuthorityChange={setAuthorityDominance}
            onEnergyChange={setEnergyLevel}
            onGenderChange={setGenderPresentation}
            onGenerate={handleGenerate}
            onLanguageChange={setLanguage}
            onMaxNewTokensChange={setMaxNewTokens}
            onOutputFormatChange={setOutputFormat}
            onPaceChange={setSpeakingPace}
            onPauseChange={setDramaticPauseIntensity}
            onPitchChange={setPitch}
            onReturnBase64Change={setReturnBase64}
            onRoughnessChange={setRoughnessGrit}
            onSampleRateChange={setSampleRate}
            onTextChange={setText}
            onToggleTone={toggleEmotionalTone}
            onVocalWeightChange={setVocalWeight}
            onWarmthChange={setWarmthColdness}
            outputFormat={outputFormat}
            pitch={pitch}
            returnBase64={returnBase64}
            roughnessGrit={roughnessGrit}
            sampleRate={sampleRate}
            speakingPace={speakingPace}
            text={text}
            vocalWeight={vocalWeight}
            warmthColdness={warmthColdness}
            accentPronunciation={accentPronunciation}
          />
        ) : (
          <VoicePresetsTab
            applyingPresetId={applyingPresetId}
            isLoadingPresets={isLoadingPresets}
            onApplyPreset={handleApplyPreset}
            onReload={fetchPresets}
            presetLoadError={presetLoadError}
            presets={presets}
          />
        )}
      </section>

      {infoMessage ? <p className={styles.statusMessage}>{infoMessage}</p> : null}
      {latestResponse ? (
        <section className={`neon-panel ${styles.responseCard}`}>
          <h2 className={styles.responseHeading}>Latest API Response</h2>
          <pre className={styles.responsePre}>{prettyJson(latestResponse)}</pre>
        </section>
      ) : null}
    </div>
  );
}
