import React, { useEffect, useMemo, useRef, useState } from "react";
import { Animated, Easing, View, StyleSheet, AccessibilityInfo } from "react-native";
import Svg, { Defs, RadialGradient, LinearGradient, Stop, Circle, Ellipse } from "react-native-svg";
import { colors as theme } from "../theme";

export type OrbState = "idle" | "connecting" | "listening" | "speaking";

type Props = {
  state?: OrbState;
  size?: number;
};

// Electric Purple / Neon Blue / Cyan across every state — only the mix and
// intensity shifts, so the orb always reads as the same VoxMate identity.
const STATE_COLORS: Record<
  OrbState,
  { glowA: string; glowB: string; barStops: string[]; barOpacity: number }
> = {
  idle: {
    glowA: theme.blue,
    glowB: theme.purple,
    barStops: [theme.cyan, theme.purpleSoft, theme.blue],
    barOpacity: 0.5,
  },
  connecting: {
    glowA: theme.purple,
    glowB: theme.blue,
    barStops: [theme.purpleSoft, theme.purple, theme.cyan],
    barOpacity: 0.7,
  },
  listening: {
    glowA: theme.cyan,
    glowB: theme.purple,
    barStops: [theme.cyan, theme.blue, theme.purple],
    barOpacity: 1,
  },
  speaking: {
    glowA: theme.purple,
    glowB: theme.cyan,
    barStops: [theme.purpleSoft, theme.purple, theme.cyan],
    barOpacity: 1,
  },
};

const STATE_TIMING: Record<OrbState, { pulseMs: number; pulseTo: number; rotateMs: number }> = {
  idle: { pulseMs: 2600, pulseTo: 1.035, rotateMs: 16000 },
  connecting: { pulseMs: 650, pulseTo: 1.08, rotateMs: 3200 },
  listening: { pulseMs: 620, pulseTo: 1.09, rotateMs: 6000 },
  speaking: { pulseMs: 400, pulseTo: 1.12, rotateMs: 4200 },
};

// Relative resting heights (0-1) for a 9-bar waveform, shaped like a gentle
// hump — matches the "single reactive waveform across the orb" reference.
const BAR_PATTERN = [0.26, 0.5, 0.78, 1, 0.86, 0.6, 0.4, 0.55, 0.3];

function hexToRgb(hex: string) {
  const v = hex.replace("#", "");
  return {
    r: parseInt(v.substring(0, 2), 16),
    g: parseInt(v.substring(2, 4), 16),
    b: parseInt(v.substring(4, 6), 16),
  };
}

// Interpolates across N color stops at position t (0-1).
function interpolateStops(stops: string[], t: number) {
  const clamped = Math.max(0, Math.min(1, t));
  const segments = stops.length - 1;
  const pos = clamped * segments;
  const idx = Math.min(segments - 1, Math.floor(pos));
  const localT = pos - idx;
  const a = hexToRgb(stops[idx]);
  const b = hexToRgb(stops[idx + 1]);
  const r = Math.round(a.r + (b.r - a.r) * localT);
  const g = Math.round(a.g + (b.g - a.g) * localT);
  const bch = Math.round(a.b + (b.b - a.b) * localT);
  return `rgb(${r},${g},${bch})`;
}

function useBarLoop(active: boolean, seed: number, slow: boolean) {
  const value = useRef(new Animated.Value(0.45)).current;
  useEffect(() => {
    if (!active) {
      Animated.timing(value, { toValue: 0.45, duration: 220, useNativeDriver: true }).start();
      return;
    }
    const duration = (slow ? 900 : 340) + seed * (slow ? 160 : 70);
    const peak = slow ? 0.72 : 1;
    const trough = slow ? 0.4 : 0.3;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(value, {
          toValue: peak,
          duration,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(value, {
          toValue: trough,
          duration: duration * 0.85,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [active, seed, slow, value]);
  return value;
}

function Waveform({
  stops,
  opacity,
  active,
  slow,
  width,
  height,
}: {
  stops: string[];
  opacity: number;
  active: boolean;
  slow: boolean;
  width: number;
  height: number;
}) {
  const barCount = BAR_PATTERN.length;
  const gap = width * 0.028;
  const barWidth = Math.max(2, (width - gap * (barCount - 1)) / barCount);

  const loops = BAR_PATTERN.map((_, i) => useBarLoop(active, i % 4, slow));

  return (
    <View style={{ width, height, flexDirection: "row", alignItems: "center", justifyContent: "center" }}>
      {BAR_PATTERN.map((h, i) => {
        const color = interpolateStops(stops, i / (barCount - 1));
        return (
          <Animated.View
            key={i}
            style={{
              width: barWidth,
              height: height * h,
              marginHorizontal: gap / 2,
              borderRadius: barWidth / 2,
              backgroundColor: color,
              opacity,
              transform: [{ scaleY: loops[i] }],
              shadowColor: color,
              shadowOpacity: 0.85,
              shadowRadius: 5,
              shadowOffset: { width: 0, height: 0 },
            }}
          />
        );
      })}
    </View>
  );
}

/**
 * Reactive AI Voice Orb — a dark convex glass sphere with a rotating
 * gradient rim, soft outer glow, a floor-glow reflection beneath it, and a
 * single continuous audio-reactive waveform (cyan → purple → blue) running
 * across its center — matching the "Futuristic Neon + Premium Minimal"
 * VoxMate identity (electric purple / neon blue / cyan throughout).
 *
 * Color/pulse speed shifts per state:
 *  - idle: gentle ambient breathing, waveform nearly still
 *  - connecting: quicker neutral pulse, waveform waking up
 *  - listening: brighter, cyan-leaning stops, waveform actively animating
 *  - speaking: brightest, purple-leaning stops, waveform driven hard
 */
export default function VoiceAssistantOrb({ state = "idle", size = 140 }: Props) {
  const pulse = useRef(new Animated.Value(1)).current;
  const rotation = useRef(new Animated.Value(0)).current;
  const listenGlow = useRef(new Animated.Value(0)).current;
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled?.()
      .then((enabled) => mounted && setReduceMotion(!!enabled))
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const { pulseMs, pulseTo, rotateMs } = STATE_TIMING[state];

    if (reduceMotion) {
      pulse.setValue(1);
      return;
    }

    pulse.setValue(1);
    const pulseLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: pulseTo,
          duration: pulseMs,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: pulseMs,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );

    rotation.setValue(0);
    const rotateLoop = Animated.loop(
      Animated.timing(rotation, {
        toValue: 1,
        duration: rotateMs,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );

    pulseLoop.start();
    rotateLoop.start();

    return () => {
      pulseLoop.stop();
      rotateLoop.stop();
    };
  }, [state, reduceMotion, pulse, rotation]);

  useEffect(() => {
    if (reduceMotion || state !== "listening") {
      listenGlow.setValue(0);
      return;
    }
    listenGlow.setValue(0);
    const glowLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(listenGlow, {
          toValue: 1,
          duration: 700,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(listenGlow, {
          toValue: 0,
          duration: 700,
          easing: Easing.in(Easing.quad),
          useNativeDriver: true,
        }),
      ])
    );
    glowLoop.start();
    return () => glowLoop.stop();
  }, [state, reduceMotion, listenGlow]);

  const colors = STATE_COLORS[state];
  const spin = rotation.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });
  const barsActive = !reduceMotion;
  const isListening = state === "listening";

  const outerSize = size * 1.7;
  const ringSize = size * 1.18;
  const coreSize = size;
  const floorSize = size * 1.9;
  const waveformWidth = coreSize * 0.66;
  const waveformHeight = coreSize * 0.36;

  const uid = useMemo(() => Math.random().toString(36).slice(2, 8), []);

  return (
    <View style={{ width: outerSize, height: outerSize + floorSize * 0.22, alignItems: "center" }}>
      <View style={{ width: outerSize, height: outerSize, alignItems: "center", justifyContent: "center" }}>
        {/* Soft elliptical floor glow / reflection beneath the orb */}
        <View style={[styles.absoluteCenter, { width: floorSize, height: floorSize * 0.4, top: outerSize * 0.62 }]}>
          <Svg width={floorSize} height={floorSize * 0.4}>
            <Defs>
              <RadialGradient id={`floor-${uid}`} cx="50%" cy="50%" r="50%">
                <Stop offset="0%" stopColor={colors.glowA} stopOpacity={0.35} />
                <Stop offset="55%" stopColor={colors.glowB} stopOpacity={0.16} />
                <Stop offset="100%" stopColor={colors.glowB} stopOpacity={0} />
              </RadialGradient>
            </Defs>
            <Ellipse cx={floorSize / 2} cy={floorSize * 0.2} rx={floorSize / 2} ry={floorSize * 0.2} fill={`url(#floor-${uid})`} />
          </Svg>
        </View>

        {/* Outer blurred glow — pulses with state */}
        <Animated.View
          style={[styles.absoluteCenter, { width: outerSize, height: outerSize, transform: [{ scale: pulse }] }]}
        >
          <Svg width={outerSize} height={outerSize}>
            <Defs>
              <RadialGradient id={`outerGlowA-${uid}`} cx="34%" cy="45%" r="55%">
                <Stop offset="0%" stopColor={colors.glowA} stopOpacity={0.55} />
                <Stop offset="100%" stopColor={colors.glowA} stopOpacity={0} />
              </RadialGradient>
              <RadialGradient id={`outerGlowB-${uid}`} cx="70%" cy="58%" r="55%">
                <Stop offset="0%" stopColor={colors.glowB} stopOpacity={0.48} />
                <Stop offset="100%" stopColor={colors.glowB} stopOpacity={0} />
              </RadialGradient>
            </Defs>
            <Circle cx={outerSize / 2} cy={outerSize / 2} r={outerSize / 2} fill={`url(#outerGlowA-${uid})`} />
            <Circle cx={outerSize / 2} cy={outerSize / 2} r={outerSize / 2} fill={`url(#outerGlowB-${uid})`} />
          </Svg>
        </Animated.View>

        {/* Rotating gradient rim */}
        <Animated.View
          style={[styles.absoluteCenter, { width: ringSize, height: ringSize, transform: [{ rotate: spin }] }]}
        >
          <Svg width={ringSize} height={ringSize}>
            <Defs>
              <LinearGradient id={`ringGrad-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <Stop offset="0%" stopColor={colors.barStops[0]} stopOpacity={0.95} />
                <Stop offset="50%" stopColor="#FFFFFF" stopOpacity={0.2} />
                <Stop offset="100%" stopColor={colors.barStops[2]} stopOpacity={0.95} />
              </LinearGradient>
            </Defs>
            <Circle
              cx={ringSize / 2}
              cy={ringSize / 2}
              r={ringSize / 2 - 3}
              stroke={`url(#ringGrad-${uid})`}
              strokeWidth={2.5}
              fill="none"
              opacity={0.9}
            />
          </Svg>
        </Animated.View>

        {/* Extra glowing ring — pulses outward only while actively listening */}
        <Animated.View
          pointerEvents="none"
          style={[
            styles.absoluteCenter,
            {
              width: ringSize,
              height: ringSize,
              opacity: listenGlow.interpolate({ inputRange: [0, 1], outputRange: [0, 0.9] }),
              transform: [
                { scale: listenGlow.interpolate({ inputRange: [0, 1], outputRange: [1, 1.22] }) },
              ],
            },
          ]}
        >
          <Svg width={ringSize} height={ringSize}>
            <Defs>
              <RadialGradient id={`listenGlow-${uid}`} cx="50%" cy="50%" r="50%">
                <Stop offset="72%" stopColor={theme.cyan} stopOpacity={0} />
                <Stop offset="88%" stopColor={theme.cyan} stopOpacity={0.55} />
                <Stop offset="100%" stopColor={theme.cyan} stopOpacity={0} />
              </RadialGradient>
            </Defs>
            <Circle cx={ringSize / 2} cy={ringSize / 2} r={ringSize / 2} fill={`url(#listenGlow-${uid})`} />
          </Svg>
        </Animated.View>

        {/* Core glass sphere — dark convex glass with rim light + specular highlight */}
        <View style={[styles.absoluteCenter, { width: coreSize, height: coreSize }]}>
          <Svg width={coreSize} height={coreSize}>
            <Defs>
              <RadialGradient id={`core-${uid}`} cx="42%" cy="38%" r="68%">
                <Stop offset="0%" stopColor="#171B21" stopOpacity={1} />
                <Stop offset="55%" stopColor="#020304" stopOpacity={1} />
                <Stop offset="100%" stopColor="#000000" stopOpacity={1} />
              </RadialGradient>
              <RadialGradient id={`coolWash-${uid}`} cx="22%" cy="55%" r="55%">
                <Stop offset="0%" stopColor={colors.glowA} stopOpacity={0.28} />
                <Stop offset="100%" stopColor={colors.glowA} stopOpacity={0} />
              </RadialGradient>
              <RadialGradient id={`warmWash-${uid}`} cx="78%" cy="60%" r="55%">
                <Stop offset="0%" stopColor={colors.glowB} stopOpacity={0.28} />
                <Stop offset="100%" stopColor={colors.glowB} stopOpacity={0} />
              </RadialGradient>
              <RadialGradient id={`highlight-${uid}`} cx="50%" cy="50%" r="50%">
                <Stop offset="0%" stopColor="#FFFFFF" stopOpacity={0.6} />
                <Stop offset="100%" stopColor="#FFFFFF" stopOpacity={0} />
              </RadialGradient>
              <RadialGradient id={`rim-${uid}`} cx="50%" cy="50%" r="50%">
                <Stop offset="86%" stopColor="#FFFFFF" stopOpacity={0} />
                <Stop offset="97%" stopColor="#FFFFFF" stopOpacity={0.22} />
                <Stop offset="100%" stopColor="#FFFFFF" stopOpacity={0} />
              </RadialGradient>
            </Defs>
            <Circle cx={coreSize / 2} cy={coreSize / 2} r={coreSize / 2 - 4} fill={`url(#core-${uid})`} />
            <Circle cx={coreSize / 2} cy={coreSize / 2} r={coreSize / 2 - 4} fill={`url(#coolWash-${uid})`} />
            <Circle cx={coreSize / 2} cy={coreSize / 2} r={coreSize / 2 - 4} fill={`url(#warmWash-${uid})`} />
            <Circle cx={coreSize / 2} cy={coreSize / 2} r={coreSize / 2 - 4} fill={`url(#rim-${uid})`} />
            <Circle
              cx={coreSize * 0.34}
              cy={coreSize * 0.3}
              r={coreSize * 0.13}
              fill={`url(#highlight-${uid})`}
            />
          </Svg>
        </View>

        {/* Center content: single continuous reactive waveform */}
        <View style={styles.absoluteCenter}>
          <Waveform
            stops={colors.barStops}
            opacity={colors.barOpacity}
            active={barsActive}
            slow={state === "idle"}
            width={waveformWidth}
            height={waveformHeight}
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  absoluteCenter: { position: "absolute", alignItems: "center", justifyContent: "center" },
});
