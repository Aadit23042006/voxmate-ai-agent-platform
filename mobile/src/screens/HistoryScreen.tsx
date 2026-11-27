import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BlurView } from "expo-blur";
import AuroraBackground from "../components/AuroraBackground";
import { colors } from "../theme";
import {
  getSearchHistory,
  deleteSearchHistoryItem,
  SearchHistoryItem,
} from "../services/api";

type Props = {
  token: string;
  onBack: () => void;
};

// Shows the signed-in user's past searches (query + answer + sources),
// most recent first. Pull to refresh; swipe-free tap-to-delete via the X.
export default function HistoryScreen({ token, onBack }: Props) {
  const [items, setItems] = useState<SearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await getSearchHistory(token);
      setItems(data);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load history");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = () => {
    setRefreshing(true);
    load();
  };

  const onDelete = async (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
    try {
      await deleteSearchHistoryItem(token, id);
    } catch {
      load();
    }
  };

  return (
    <AuroraBackground style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <BlurView intensity={40} tint="dark" style={StyleSheet.absoluteFill} />
          <Ionicons name="chevron-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Search History</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color="#fff" />
      ) : error ? (
        <Text style={styles.errorText}>{error}</Text>
      ) : items.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="time-outline" size={40} color="#666" />
          <Text style={styles.emptyText}>No searches yet</Text>
          <Text style={styles.emptySubtext}>
            Things you ask VoxMate to search for will show up here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ paddingBottom: 24 }}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#fff" />
          }
          renderItem={({ item }) => (
            <View style={styles.card}>
              <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 14 }]} />
              <View style={styles.cardHeader}>
                <Text style={styles.query} numberOfLines={2}>
                  {item.query}
                </Text>
                <TouchableOpacity onPress={() => onDelete(item.id)} hitSlop={8}>
                  <Ionicons name="close" size={18} color="#888" />
                </TouchableOpacity>
              </View>
              {item.answer && (
                <Text style={styles.answer} numberOfLines={4}>
                  {item.answer}
                </Text>
              )}
              {item.sources && item.sources.length > 0 && (
                <Text style={styles.sources} numberOfLines={1}>
                  Sources: {item.sources.map((s) => s.title || s.url).filter(Boolean).join(", ")}
                </Text>
              )}
              <Text style={styles.timestamp}>
                {new Date(item.created_at).toLocaleString()}
              </Text>
            </View>
          )}
        />
      )}
    </AuroraBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 60, paddingHorizontal: 16 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  title: { color: "#fff", fontSize: 18, fontWeight: "700" },
  errorText: { color: colors.error, marginTop: 24, textAlign: "center" },
  emptyState: { alignItems: "center", marginTop: 80 },
  emptyText: { color: "#fff", fontSize: 16, fontWeight: "600", marginTop: 12 },
  emptySubtext: {
    color: "#888",
    fontSize: 13,
    textAlign: "center",
    marginTop: 6,
    paddingHorizontal: 40,
  },
  card: {
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    padding: 14,
    marginBottom: 10,
    overflow: "hidden",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
  },
  query: { color: "#fff", fontSize: 15, fontWeight: "600", flex: 1, marginRight: 8 },
  answer: { color: "#CFCFE0", fontSize: 13, marginTop: 6, lineHeight: 18 },
  sources: { color: "#888", fontSize: 11, marginTop: 8 },
  timestamp: { color: "#666", fontSize: 11, marginTop: 6 },
});
