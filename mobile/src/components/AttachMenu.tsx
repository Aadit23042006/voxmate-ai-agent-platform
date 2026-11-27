import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, Modal, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BlurView } from "expo-blur";
import { colors } from "../theme";

type Props = {
  visible: boolean;
  onClose: () => void;
  onTakePhoto: () => void;
  onUploadPhoto: () => void;
  onUploadFile: () => void;
  onScreenScreenshot: () => void;
};

// Bottom-sheet style menu shown from the (+) button, with a distinct
// icon for each attach action instead of a plain text list.
export default function AttachMenu({
  visible,
  onClose,
  onTakePhoto,
  onUploadPhoto,
  onUploadFile,
  onScreenScreenshot,
}: Props) {
  const pick = (action: () => void) => {
    onClose();
    action();
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <BlurView intensity={55} tint="dark" style={StyleSheet.absoluteFill} />
          <View style={styles.handle} />
          <Text style={styles.title}>Add to VoxMate</Text>

          <View style={styles.row}>
            <TouchableOpacity style={styles.option} onPress={() => pick(onScreenScreenshot)}>
              <View style={[styles.iconCircle, { backgroundColor: "rgba(0,217,255,0.18)" }]}>
                <Ionicons name="scan-outline" size={26} color="#00D9FF" />
              </View>
              <Text style={styles.optionLabel}>Screen</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.option} onPress={() => pick(onTakePhoto)}>
              <View style={[styles.iconCircle, { backgroundColor: "rgba(255,122,69,0.18)" }]}>
                <Ionicons name="camera-outline" size={26} color="#FF7A45" />
              </View>
              <Text style={styles.optionLabel}>Camera</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.option} onPress={() => pick(onUploadPhoto)}>
              <View style={[styles.iconCircle, { backgroundColor: "rgba(76,110,245,0.18)" }]}>
                <Ionicons name="image-outline" size={26} color="#4C6EF5" />
              </View>
              <Text style={styles.optionLabel}>Upload Photo</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.option} onPress={() => pick(onUploadFile)}>
              <View style={[styles.iconCircle, { backgroundColor: "rgba(80,200,140,0.18)" }]}>
                <Ionicons name="document-outline" size={26} color="#50C88C" />
              </View>
              <Text style={styles.optionLabel}>Upload File</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: "rgba(11,16,36,0.8)",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    borderBottomWidth: 0,
    paddingTop: 10,
    paddingBottom: 30,
    paddingHorizontal: 20,
    overflow: "hidden",
  },
  handle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: "rgba(255,255,255,0.2)",
    alignSelf: "center",
    marginBottom: 14,
  },
  title: { color: "#fff", fontSize: 15, fontWeight: "600", marginBottom: 18, textAlign: "center" },
  row: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-around", marginBottom: 12, gap: 10 },
  option: { alignItems: "center", width: 72 },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  optionLabel: { color: "#EDEDED", fontSize: 12, textAlign: "center" },
  cancelButton: {
    marginTop: 8,
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 14,
    height: 46,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelText: { color: "#fff", fontWeight: "600", fontSize: 14 },
});
