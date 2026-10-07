import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Image,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useFonts, Pacifico_400Regular } from '@expo-google-fonts/pacifico';

import { fetchSavedItems } from '@/api/savedItems';
import { AddItemModal } from '@/components/add-item-modal';
import { ItemDetailModal } from '@/components/item-detail-modal';
import { Button } from '@/components/ui/Button';
import { SearchBar } from '@/components/ui/SearchBar';
import { ItemCard } from '@/components/ItemCard';
import { ThemedText } from '@/components/themed-text';
import { BottomTabInset, Colors, Spacing } from '@/constants/theme';
import { useAuth } from '@/context/AuthContext';
import { fetchCategories } from '@/api/categories';
import { ManageCategoriesModal } from '@/components/manage-categories-modal';
import { CategoryChip } from '@/components/category-chip';
import { ProfileModal } from '@/components/profile-modal';
import { useShareIntent } from 'expo-share-intent';
import { fetchProfile } from '@/api/profile';
import { getErrorMessage } from '@/utils/errors';

const POLL_INTERVAL_MS = 4000;

type StatusFilter = 'to_do' | 'completed';

export default function HomeScreen() {
  const { logout } = useAuth();

  const [items, setItems] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadingRef = useRef(false);
  const pageRef = useRef(1);
  const hasMoreRef = useRef(true);

  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [addVisible, setAddVisible] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('to_do');

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const itemsRef = useRef<any[]>([]);
  const statusRef = useRef<StatusFilter>('to_do');

  const [categories, setCategories] = useState<any[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null);
  const [manageCategoriesVisible, setManageCategoriesVisible] = useState(false);

  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntent();
  const [sharedUrl, setSharedUrl] = useState('');
  const [sharedName, setSharedName] = useState('');

  const [retentionDays, setRetentionDays] = useState(7);
  const [isPremium, setIsPremium] = useState(false);

  const loadProfile = useCallback(() => {
    fetchProfile()
      .then((data) => {
        setRetentionDays(data.completed_items_retention_days);
        const premium =
          data.plan === 'PR' &&
          data.premium_until &&
          new Date(data.premium_until) >= new Date(new Date().toDateString());
        setIsPremium(!!premium);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const [fontsLoaded] = useFonts({
    Pacifico_400Regular,
  });

  const [profileVisible, setProfileVisible] = useState(false);

  useEffect(() => {
    if (!hasShareIntent) return;

    const url = shareIntent.webUrl ?? '';
    const text = shareIntent.text ?? '';

    setSharedUrl(url || (text.startsWith('http') ? text : ''));
    setSharedName(url ? '' : text);
    setAddVisible(true);
  }, [hasShareIntent, shareIntent]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 400);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const loadCategories = useCallback(() => {
    fetchCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    statusRef.current = statusFilter;
  }, [statusFilter]);

  const load = useCallback(
    async (pageToLoad: number, replace: boolean) => {
      if (loadingRef.current) return;

      loadingRef.current = true;
      setLoading(true);
      setError('');

      try {
        const data = await fetchSavedItems(
          pageToLoad,
          statusFilter,
          categoryFilter ?? undefined,
          debouncedSearch.trim() || undefined
        );

        setItems((prev) =>
          replace ? data.results : [...prev, ...data.results],
        );

        setPage(pageToLoad);
        pageRef.current = pageToLoad;

        const nextExists = !!data.next;
        setHasMore(nextExists);
        hasMoreRef.current = nextExists;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Could not load your items.'));
      } finally {
        loadingRef.current = false;
        setLoading(false);
        setRefreshing(false);
      }
    },
    [statusFilter, categoryFilter, debouncedSearch],
  );

  useEffect(() => {
    setItems([]);

    pageRef.current = 1;
    hasMoreRef.current = true;

    load(1, true);
  }, [load]);

  useEffect(() => {
    const timer = setInterval(async () => {
      const hasPending = itemsRef.current.some(
        (i) =>
          i.extraction_status === 'pending' ||
          i.extraction_status === 'processing',
      );

      if (!hasPending) return;

      try {
        const data = await fetchSavedItems(1, statusRef.current, undefined, debouncedSearch.trim() || undefined);

        const fresh = new Map(
          data.results.map((i: any) => [i.id, i]),
        );

        setItems((prev) =>
          prev.map((i) => fresh.get(i.id) ?? i),
        );
      } catch {}
    }, POLL_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [debouncedSearch]);

  const onRefresh = () => {
    setRefreshing(true);

    pageRef.current = 1;
    hasMoreRef.current = true;

    load(1, true);
  };

  const onEndReached = () => {
    if (
      loadingRef.current ||
      !hasMoreRef.current ||
      items.length === 0
    ) {
      return;
    }

    load(pageRef.current + 1, false);
  };

  const handleUpdated = (updated: any) => {
    setItems((prev) =>
      updated.status !== statusFilter
        ? prev.filter((i) => i.id !== updated.id)
        : prev.map((i) =>
            i.id === updated.id ? updated : i,
          ),
    );
  };

  const handleDeleted = (id: number) => {
    setItems((prev) =>
      prev.filter((i) => i.id !== id),
    );
  };

  // منتظر ماندن برای لود کامل فونت‌ها
  if (!fontsLoaded) {
    return null;
  }

  return (
    <LinearGradient
      colors={['#FFFFFF', '#F8F9FA', '#F2F2F7']}
      style={styles.container}
    >
      <SafeAreaView style={styles.safeArea}>

        {/* Header با آیکون مدرن اپلیکیشن */}
        <View style={styles.header}>
          <View style={styles.brandContainer}>
            <Image
              source={require('@/assets/images/icon.png')}
              style={styles.brandIcon}
            />
            <ThemedText style={styles.logo}>Mibinish</ThemedText>
          </View>

          <View style={styles.headerButtons}>
            <Pressable
              style={styles.iconButton}
              onPress={() => setProfileVisible(true)}
              hitSlop={8}>
              <Ionicons name="person-circle-outline" size={26} color="#1C1C1E" />
            </Pressable>
            <Pressable
              style={styles.addButton}
              onPress={() => setAddVisible(true)}
              hitSlop={8}>
              <Ionicons name="add" size={20} color="#FFFFFF" />
              <ThemedText style={styles.addButtonText}>Add</ThemedText>
            </Pressable>
          </View>
        </View>

        {/* سرچ‌بار نوین */}
        <SearchBar
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search items, URLs, sources..."
        />
      
        {/* فیلتر status (To do / Done) به‌صورت Segmented Control مدرن */}
        <View style={styles.segmentedControl}>
          <Pressable
            style={[
              styles.segmentTab,
              statusFilter === 'to_do' && styles.activeSegmentTab,
            ]}
            onPress={() => setStatusFilter('to_do')}>
            <ThemedText
              style={[
                styles.segmentText,
                statusFilter === 'to_do' && styles.activeSegmentText,
              ]}>
              To Do
            </ThemedText>
          </Pressable>

          <Pressable
            style={[
              styles.segmentTab,
              statusFilter === 'completed' && styles.activeSegmentTab,
            ]}
            onPress={() => setStatusFilter('completed')}>
            <ThemedText
              style={[
                styles.segmentText,
                statusFilter === 'completed' && styles.activeSegmentText,
              ]}>
              Done
            </ThemedText>
          </Pressable>
        </View>

        {/* دسته‌بندی‌ها */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.categoryScroll}
          contentContainerStyle={styles.categoryFilters}>
          <CategoryChip
            label="All"
            selected={categoryFilter === null}
            onPress={() => setCategoryFilter(null)}
          />
          {categories.map((cat) => (
            <CategoryChip
              key={cat.id}
              label={cat.name}
              color={cat.color}
              selected={categoryFilter === cat.id}
              onPress={() => setCategoryFilter(cat.id)}
            />
          ))}
          <Button
            title="+ Manage"
            variant="ghost"
            onPress={() => setManageCategoriesVisible(true)}
            style={styles.manageButton}
          />
        </ScrollView>

        {error ? (
          <ThemedText style={styles.error}>
            {error}
          </ThemedText>
        ) : null}

        {/* لیست اصلی آیتم‌ها با استفاده از ItemCard */}
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          refreshing={refreshing}
          onRefresh={onRefresh}
          onEndReached={onEndReached}
          onEndReachedThreshold={0.4}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}

          ListEmptyComponent={
            !loading ? (
              <View style={styles.emptyContainer}>
                <Ionicons name="bookmark-outline" size={48} color="#C7C7CC" />
                <ThemedText style={styles.empty}>
                  {debouncedSearch
                    ? 'No items found matching your search.'
                    : statusFilter === 'to_do'
                    ? 'Nothing to do yet. Save your first link!'
                    : 'No completed items.'}
                </ThemedText>
              </View>
            ) : null
          }

          ListFooterComponent={
            loading && !refreshing ? (
              <ActivityIndicator style={styles.footerLoader} color="#007AFF" />
            ) : null
          }

          renderItem={({ item }) => (
            <ItemCard item={item} onPress={() => setSelected(item)} retentionDays={retentionDays} />
          )}
        />

        <AddItemModal
          visible={addVisible}
          initialUrl={sharedUrl}
          initialName={sharedName}
          onClose={() => {
            setAddVisible(false);
            setSharedUrl('');
            setSharedName('');
            resetShareIntent();
          }}
          onCreated={() => {
            setStatusFilter('to_do');
            load(1, true);
          }}
        />

        <ItemDetailModal
          item={selected}
          onClose={() => setSelected(null)}
          onUpdated={handleUpdated}
          onDeleted={handleDeleted}
          retentionDays={retentionDays}
          isPremium={isPremium}
        />

        <ManageCategoriesModal
          visible={manageCategoriesVisible}
          onClose={() => setManageCategoriesVisible(false)}
          onChanged={loadCategories}
        />

        <ProfileModal
          visible={profileVisible}
          onClose={() => {
            setProfileVisible(false);
            loadProfile();
          }}
        />

      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.three,
    paddingBottom: BottomTabInset - 60,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Spacing.two,
    paddingBottom: Spacing.one,
  },
  brandContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandIcon: {
    width: 28,
    height: 28,
    // borderRadius: 3,
  },
  logo: {
    fontSize: 20,
    color: '#1C1C1E',
    fontFamily: 'Pacifico_400Regular',
    paddingVertical: 8,
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  iconButton: {
    padding: 4,
  },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1C1C1E',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 2,
  },
  addButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 14,
  },
  segmentedControl: {
    flexDirection: 'row',
    backgroundColor: 'rgba(118, 118, 128, 0.12)',
    borderRadius: 10,
    padding: 2,
    marginBottom: Spacing.two,
  },
  segmentTab: {
    flex: 1,
    paddingVertical: 7,
    alignItems: 'center',
    borderRadius: 8,
  },
  activeSegmentTab: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  segmentText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#8E8E93',
  },
  activeSegmentText: {
    color: '#1C1C1E',
    fontWeight: '600',
  },
  categoryScroll: {
    flexGrow: 0,
    maxHeight: 44,
    marginBottom: Spacing.two,
  },
  categoryFilters: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
  },
  manageButton: {
    height: 64,
    paddingHorizontal: Spacing.two,
  },
  list: {
    paddingBottom: Spacing.four,
  },
  error: {
    color: Colors.light.danger,
    textAlign: 'center',
    marginBottom: Spacing.two,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: Spacing.four * 2,
    gap: Spacing.two,
  },
  empty: {
    color: '#8E8E93',
    textAlign: 'center',
    fontSize: 15,
  },
  footerLoader: {
    marginVertical: Spacing.three,
  },
});