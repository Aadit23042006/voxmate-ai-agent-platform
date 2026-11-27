import React from "react";
import { View, StyleSheet, useWindowDimensions, ViewStyle, StyleProp } from "react-native";
import Svg, { Defs, RadialGradient, Stop, Rect, Ellipse } from "react-native-svg";
import { colors } from "../theme";

type Props = {
  children?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
};

// Deep midnight-navy base with restrained electric-purple / neon-blue /
// cyan glow pockets — "Futuristic Neon + Premium Minimal". Kept subtle on
// purpose (low opacities, soft falloff) so it reads as a premium AI-OS
// surface, not a cyberpunk backdrop. Used behind every screen.
export default function AuroraBackground({ children, style }: Props) {
  const { width, height } = useWindowDimensions();

  return (
    <View style={[styles.root, style]}>
      <Svg width={width} height={height} style={StyleSheet.absoluteFill}>
        <Defs>
          <RadialGradient id="base" cx="50%" cy="22%" r="80%">
            <Stop offset="0%" stopColor={colors.bgSecondary} stopOpacity={1} />
            <Stop offset="100%" stopColor={colors.bg} stopOpacity={1} />
          </RadialGradient>
          <RadialGradient id="purpleGlow" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={colors.purple} stopOpacity={0.34} />
            <Stop offset="55%" stopColor={colors.purple} stopOpacity={0.14} />
            <Stop offset="100%" stopColor={colors.purple} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="blueGlow" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={colors.blue} stopOpacity={0.3} />
            <Stop offset="45%" stopColor={colors.blue} stopOpacity={0.14} />
            <Stop offset="100%" stopColor={colors.blue} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="cyanGlow" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={colors.cyan} stopOpacity={0.16} />
            <Stop offset="100%" stopColor={colors.cyan} stopOpacity={0} />
          </RadialGradient>
        </Defs>

        {/* Base: near-black navy up top, dissolving to true black at the edges */}
        <Rect x={0} y={0} width={width} height={height} fill="url(#base)" />

        {/* Soft electric-purple bloom, held low and wide behind the orb/content */}
        <Ellipse
          cx={width * 0.5}
          cy={height * 0.98}
          rx={width * 0.9}
          ry={height * 0.5}
          fill="url(#purpleGlow)"
        />

        {/* Neon-blue glow, upper-middle, right where the orb usually sits */}
        <Ellipse cx={width * 0.42} cy={height * 0.28} rx={width * 0.55} ry={width * 0.55} fill="url(#blueGlow)" />

        {/* Faint cyan accent, lower-left */}
        <Ellipse cx={width * 0.06} cy={height * 0.7} rx={width * 0.5} ry={width * 0.5} fill="url(#cyanGlow)" />

        {/* Cyan corner glow, top-right — matches the reference's cool corner light */}
        <Ellipse cx={width * 1.0} cy={height * 0.0} rx={width * 0.55} ry={width * 0.45} fill="url(#cyanGlow)" />

        {/* Faint purple accent, top-right near the header */}
        <Ellipse cx={width * 0.86} cy={height * 0.1} rx={width * 0.3} ry={width * 0.3} fill="url(#purpleGlow)" />
      </Svg>
      <View style={styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  content: { flex: 1 },
});
