/**
 * Admin API client (browser). Every call goes through the same-origin `/api/v1` rewrite with
 * the HttpOnly session cookie and the CSRF header; FastAPI enforces authentication and
 * permissions on each request.
 */

import { apiFetch, apiSend } from "@/lib/api/client";
import type {
  AdminCategory,
  AdminCategoryDetail,
  AdminCollection,
  AdminMe,
  AdminProductDetail,
  AdminProductList,
  AdminProductSummary,
  Dashboard,
  HomepageAdmin,
  MediaAsset,
  NavigationItem,
  NavigationMenu,
  ProductPayload,
  ProductStatus,
  Publication,
  PublishStatus,
  Section,
  SectionPayload,
  ShippingRule,
  SizeChart,
  StoreSettings,
  WebsitePage,
} from "./types";

type Created = { id: string };
const q = (params: Record<string, string | number | undefined | null>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
};

export const adminApi = {
  // --- session ---
  me: () => apiFetch<AdminMe>("/admin/me"),
  login: (email: string, password: string) => apiSend<AdminMe>("POST", "/auth/login", { email, password }),
  logout: () => apiSend<void>("POST", "/auth/logout"),
  dashboard: () => apiFetch<Dashboard>("/admin/dashboard"),

  // --- products ---
  products: (params: { page?: number; q?: string; status?: ProductStatus | ""; page_size?: number }) =>
    apiFetch<AdminProductList>(`/admin/products${q({ page_size: 24, sort: "newest", ...params })}`),
  product: (id: string) => apiFetch<AdminProductDetail>(`/admin/products/${id}`),
  createProduct: (body: ProductPayload) => apiSend<AdminProductDetail>("POST", "/admin/products", body),
  updateProduct: (id: string, body: ProductPayload) =>
    apiSend<AdminProductDetail>("PUT", `/admin/products/${id}`, body),
  setProductStatus: (id: string, status: ProductStatus) =>
    apiSend<AdminProductDetail>("PATCH", `/admin/products/${id}/status`, { status }),
  duplicateProduct: (id: string) => apiSend<AdminProductDetail>("POST", `/admin/products/${id}/duplicate`),

  // --- categories ---
  categories: () => apiFetch<AdminCategory[]>("/admin/categories"),
  category: (id: string) => apiFetch<AdminCategoryDetail>(`/admin/categories/${id}`),
  createCategory: (body: Record<string, unknown>) => apiSend<Created>("POST", "/admin/categories", body),
  updateCategory: (id: string, body: Record<string, unknown>) =>
    apiSend<void>("PUT", `/admin/categories/${id}`, body),
  setCategoryActive: (id: string, is_active: boolean) =>
    apiSend<void>("PATCH", `/admin/categories/${id}/status`, { is_active }),
  setCategoryProducts: (id: string, product_ids: string[]) =>
    apiSend<void>("PUT", `/admin/categories/${id}/products`, { product_ids }),

  // --- collections ---
  collections: () => apiFetch<AdminCollection[]>("/admin/collections"),
  collection: (id: string) => apiFetch<AdminCollection>(`/admin/collections/${id}`),
  createCollection: (body: Record<string, unknown>) => apiSend<Created>("POST", "/admin/collections", body),
  updateCollection: (id: string, body: Record<string, unknown>) =>
    apiSend<void>("PUT", `/admin/collections/${id}`, body),
  setCollectionStatus: (id: string, status: PublishStatus) =>
    apiSend<void>("PATCH", `/admin/collections/${id}/status`, { status }),
  collectionProducts: (id: string) => apiFetch<AdminProductSummary[]>(`/admin/collections/${id}/products`),
  setCollectionProducts: (id: string, product_ids: string[]) =>
    apiSend<void>("PUT", `/admin/collections/${id}/products`, { product_ids }),

  // --- homepage builder ---
  homepage: () => apiFetch<HomepageAdmin>("/admin/homepage"),
  section: (id: string) => apiFetch<Section>(`/admin/homepage/sections/${id}`),
  createSection: (body: SectionPayload) => apiSend<Created>("POST", "/admin/homepage/sections", body),
  updateSection: (id: string, body: SectionPayload) =>
    apiSend<void>("PUT", `/admin/homepage/sections/${id}`, body),
  deleteSection: (id: string) => apiSend<void>("DELETE", `/admin/homepage/sections/${id}`),
  reorderSections: (ids: string[]) => apiSend<void>("PUT", "/admin/homepage/sections/order", { ids }),
  setSectionVisibility: (id: string, is_visible: boolean) =>
    apiSend<void>("PATCH", `/admin/homepage/sections/${id}/visibility`, { is_visible }),
  setSectionProducts: (id: string, product_ids: string[]) =>
    apiSend<void>("PUT", `/admin/homepage/sections/${id}/products`, { product_ids }),
  publishHomepage: (note?: string) => apiSend<Publication>("POST", "/admin/homepage/publish", { note: note || null }),

  // --- media ---
  media: (params: { purpose?: string; limit?: number; offset?: number }) =>
    apiFetch<MediaAsset[]>(`/admin/media${q({ limit: 48, ...params })}`),
  mediaAsset: (id: string) => apiFetch<MediaAsset>(`/admin/media/${id}`),
  uploadMedia: (file: File, purpose: string, alt?: string) => {
    const form = new FormData();
    form.set("file", file);
    form.set("purpose", purpose);
    if (alt) form.set("alt_text", alt);
    return apiFetch<MediaAsset>("/admin/media", { method: "POST", body: form, timeoutMs: 60000 });
  },
  replaceMedia: (id: string, file: File) => {
    const form = new FormData();
    form.set("file", file);
    return apiFetch<MediaAsset>(`/admin/media/${id}/replace`, { method: "POST", body: form, timeoutMs: 60000 });
  },
  updateMedia: (id: string, alt_text: string | null) => apiSend<MediaAsset>("PATCH", `/admin/media/${id}`, { alt_text }),
  mediaUsage: (id: string) => apiFetch<{ in_use: boolean; places: string[] }>(`/admin/media/${id}/usage`),
  deleteMedia: (id: string) => apiSend<void>("DELETE", `/admin/media/${id}`),

  // --- settings & content ---
  settings: () => apiFetch<StoreSettings>("/admin/settings"),
  updateSettings: (changes: Partial<StoreSettings>) => apiSend<StoreSettings>("PATCH", "/admin/settings", changes),
  navigation: (menu?: NavigationMenu) => apiFetch<NavigationItem[]>(`/admin/navigation${q({ menu })}`),
  createNavigation: (body: Record<string, unknown>) => apiSend<Created>("POST", "/admin/navigation", body),
  updateNavigation: (id: string, body: Record<string, unknown>) => apiSend<void>("PUT", `/admin/navigation/${id}`, body),
  deleteNavigation: (id: string) => apiSend<void>("DELETE", `/admin/navigation/${id}`),
  reorderNavigation: (ids: string[]) => apiSend<void>("PUT", "/admin/navigation/order", { ids }),
  pages: () => apiFetch<WebsitePage[]>("/admin/pages"),
  page: (id: string) => apiFetch<WebsitePage>(`/admin/pages/${id}`),
  createPage: (body: Record<string, unknown>) => apiSend<Created>("POST", "/admin/pages", body),
  updatePage: (id: string, body: Record<string, unknown>) => apiSend<void>("PUT", `/admin/pages/${id}`, body),
  deletePage: (id: string) => apiSend<void>("DELETE", `/admin/pages/${id}`),
  shippingRules: () => apiFetch<ShippingRule[]>("/admin/shipping-rules"),
  createShippingRule: (body: Record<string, unknown>) => apiSend<Created>("POST", "/admin/shipping-rules", body),
  updateShippingRule: (id: string, body: Record<string, unknown>) =>
    apiSend<void>("PUT", `/admin/shipping-rules/${id}`, body),
  deleteShippingRule: (id: string) => apiSend<void>("DELETE", `/admin/shipping-rules/${id}`),
  sizeCharts: () => apiFetch<SizeChart[]>("/admin/size-charts"),
  createSizeChart: (body: Record<string, unknown>) => apiSend<Created>("POST", "/admin/size-charts", body),
  updateSizeChart: (id: string, body: Record<string, unknown>) => apiSend<void>("PUT", `/admin/size-charts/${id}`, body),
  deleteSizeChart: (id: string) => apiSend<void>("DELETE", `/admin/size-charts/${id}`),
};

/** Ask the storefront to drop its cached CMS content (after publish/settings changes). */
export async function refreshStorefront(): Promise<boolean> {
  const csrf = document.cookie
    .split("; ")
    .find((c) => c.startsWith("tk_csrf="))
    ?.slice("tk_csrf=".length);
  const response = await fetch("/api/revalidate", {
    method: "POST",
    credentials: "same-origin",
    headers: csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {},
  }).catch(() => null);
  return Boolean(response?.ok);
}
