"use client";

import { useMemo, useState } from "react";
import styles from "./SoundDesigner.module.css";

type DesignerTab = "custom" | "presets";

type VoicePreset = {
  id: number;
  name: string;
  primary: string[];
  secondary: string[];
};

type StaticScaleProps = {
  labels: string[];
  markers: number[];
};

const voicePresets: VoicePreset[] = [
  {
    id: 1,
    name: "Alpha Mentor",
    primary: ["Masculine", "Mature", "Low Pitch", "Heavy Voice", "Slow Pace", "Dominant"],
    secondary: ["Inspirational", "Strong Pauses"],
  },
  {
    id: 2,
    name: "Wise King",
    primary: ["Masculine", "Mature", "Low Pitch", "Heavy Voice", "Slow Pace"],
    secondary: ["Calm Authoritative", "Warm Serious", "Cinematic Pauses"],
  },
  {
    id: 3,
    name: "Borderline Angry Coach",
    primary: ["Masculine", "Adult", "Low Pitch", "Heavy Voice"],
    secondary: ["Moderate-Slow", "High Intensity", "Aggressive", "Commanding"],
  },
  {
    id: 4,
    name: "Dark Cinematic Narrator",
    primary: ["Masculine", "Mature", "Very Low Pitch", "Heavy Voice"],
    secondary: ["Slow Pace", "Controlled Energy", "Serious", "Cold Tone", "Cinematic Pauses"],
  },
];

function StaticScale({ labels, markers }: StaticScaleProps) {
  return (
    <div className={styles.scaleWrap}>
      <div className={styles.scaleTrack}>
        {labels.slice(1).map((label, index) => (
          <span
            aria-hidden="true"
            className={styles.scaleDivider}
            key={`${label}-${index}`}
            style={{ left: `${((index + 1) / labels.length) * 100}%` }}
          />
        ))}
        {markers.map((position, index) => (
          <span
            aria-hidden="true"
            className={styles.scaleMarker}
            key={`marker-${position}-${index}`}
            style={{ left: `${position}%` }}
          />
        ))}
      </div>
      <div className={styles.scaleLabels}>
        {labels.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
    </div>
  );
}

function CustomDesignerTab() {
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
                  <button className={`${styles.pillButton} ${styles.pillButtonActive}`} type="button">
                    Masculine
                  </button>
                  <button className={styles.pillButton} type="button">
                    Feminine
                  </button>
                  <button className={styles.pillButton} type="button">
                    Neutral
                  </button>
                </div>
              </div>

              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Age Impression</p>
                <StaticScale labels={["Teen", "Young", "Mature", "Elder"]} markers={[38, 74]} />
              </div>

              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Accent / Pronunciation</p>
                <button className={styles.selectMock} type="button">
                  <span>Neutral English</span>
                  <span aria-hidden="true" className={styles.chevron}>
                    v
                  </span>
                </button>
              </div>
            </div>
          </section>

          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 2 - Voice Body</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Pitch</p>
                <StaticScale labels={["Very Low", "Low", "Mid", "High"]} markers={[41, 62]} />
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Vocal Weight</p>
                <StaticScale labels={["Light", "Medium", "Heavy", "Very Heavy"]} markers={[37, 76]} />
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Roughness / Grit</p>
                <StaticScale labels={["Smooth", "Slight", "Rough", "Gritty"]} markers={[43, 62, 77]} />
              </div>
            </div>
          </section>

          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 3 - Delivery</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Speaking Pace</p>
                <StaticScale labels={["Very Slow", "Slow", "Medium", "Fast"]} markers={[44, 74]} />
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Energy Level</p>
                <StaticScale labels={["Calm", "Controlled", "Intense", "Explosive"]} markers={[46, 72]} />
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Dramatic Pause Intensity</p>
                <StaticScale labels={["Minimal", "Natural", "Strong", "Cinematic"]} markers={[43, 76]} />
              </div>
            </div>
          </section>

          <section className={styles.groupCard}>
            <h2 className={styles.groupHeading}>GROUP 4 - Personality</h2>
            <div className={styles.groupBody}>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Emotional Tone</p>
                <div className={styles.pillRow}>
                  <button className={styles.pillButton} type="button">
                    Serious
                  </button>
                  <button className={`${styles.pillButton} ${styles.pillButtonActive}`} type="button">
                    Inspirational
                  </button>
                  <button className={styles.pillButton} type="button">
                    Aggressive
                  </button>
                </div>
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Authority / Dominance</p>
                <StaticScale labels={["Soft", "Balanced", "Dominant", "Commanding"]} markers={[27, 48, 72]} />
              </div>
              <div className={styles.controlRow}>
                <p className={styles.controlLabel}>Warmth vs Coldness</p>
                <StaticScale labels={["Cold", "Slight Cold", "Balanced", "Warm"]} markers={[28, 50, 73]} />
              </div>
            </div>
          </section>
        </div>

        <div className={styles.rightColumn}>
          <section className={styles.sideCard}>
            <h2 className={styles.sideHeading}>Text Input</h2>
            <div aria-label="Text input placeholder" className={styles.textInputMock} role="textbox">
              Enter motivational quote...
            </div>
          </section>

          <section className={styles.sideCard}>
            <h2 className={styles.sideHeading}>Voice Preview</h2>
            <div className={styles.previewStack}>
              <button className={styles.previewButton} type="button">
                <span className={styles.previewGlyph}>&gt;</span>
                <span>Play</span>
              </button>
              <button className={styles.previewButton} type="button">
                <span className={styles.previewGlyph}>[]</span>
                <span>Stop</span>
              </button>
            </div>
          </section>

          <section className={styles.sideCard}>
            <h2 className={styles.sideHeading}>Generate Voice</h2>
            <div className={styles.generateRow}>
              <button className={styles.generateButton} type="button">
                Generate
              </button>
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}

function VoicePresetsTab() {
  return (
    <section
      aria-labelledby="sound-designer-presets-tab"
      className={styles.contentWrap}
      id="sound-designer-presets"
      role="tabpanel"
    >
      <div className={styles.presetsList}>
        {voicePresets.map((preset) => (
          <article className={styles.presetCard} key={preset.id}>
            <h2 className={styles.presetTitle}>
              {preset.id}. {preset.name}
            </h2>
            <div className={styles.presetBody}>
              <div className={styles.presetLines}>
                <p className={styles.presetLine}>{preset.primary.join(" | ")}</p>
                <p className={styles.presetLine}>{preset.secondary.join(" | ")}</p>
              </div>
              <button className={styles.applyButton} type="button">
                Apply
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function SoundDesigner() {
  const [activeTab, setActiveTab] = useState<DesignerTab>("custom");

  const title = useMemo(
    () => (activeTab === "custom" ? "VOICE DESIGNER" : "VOICE PRESETS"),
    [activeTab]
  );

  return (
    <div className="mx-auto flex w-full max-w-[1240px] flex-col">
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

        {activeTab === "custom" ? <CustomDesignerTab /> : <VoicePresetsTab />}
      </section>
    </div>
  );
}
