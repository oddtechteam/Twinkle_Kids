/**
 * DEVELOPMENT FIXTURE — editorial defaults used until the admin CMS endpoints exist.
 *
 * Contains no products, prices, stock, reviews, statistics or business guarantees: products
 * always come from the live catalogue API. Contact details and testimonials are intentionally
 * empty, so their sections stay hidden until real data is configured. Delete this file (and
 * its import in ../index.ts) once `GET /api/v1/content` is implemented.
 */

import type { HeroMessage, SiteContent } from "../types";

/** Brand mood lines for the interactive hero stage (no product or business claims). */
export const HERO_MESSAGES: HeroMessage[] = [
  { icon: "heart", text: "Little Looks, Big Love" },
  { icon: "gift", text: "Festive Looks They’ll Love" },
  { icon: "sparkles", text: "Everyday Comfort, Extra Cute" },
  { icon: "star", text: "Tiny Trends, Big Personality" },
  { icon: "heart", text: "Made for Every Little Moment" },
  { icon: "shirt", text: "Find Their New Favourite Outfit" },
];

export const developmentContent: SiteContent = {
  source: "development-fixture",
  brand: {
    name: "Twinkle Kids",
    tagline: "Cute Styles for Little Smiles.",
    description:
      "Children's fashion boutique — adorable everyday outfits, festive looks and special occasion styles.",
  },
  theme: {},
  seo: { titleSuffix: "Twinkle Kids", description: "", ogImageUrl: null },
  defaultSort: "featured",
  announcement: {
    visible: true,
    message: "The new festive edit has arrived",
    link: { label: "Explore new arrivals", href: "/shop?sort=newest" },
  },
  navigation: {
    primary: [
      { label: "Shop All", href: "/shop" },
      { label: "New Arrivals", href: "/shop?sort=newest" },
      { label: "About Us", href: "/about" },
      { label: "Contact Us", href: "/contact" },
    ],
    mobile: [
      { label: "Home", href: "/" },
      { label: "Shop All", href: "/shop" },
      { label: "New Arrivals", href: "/shop?sort=newest" },
      { label: "About Us", href: "/about" },
      { label: "Contact Us", href: "/contact" },
    ],
  },
  homepage: {
    sections: [
      {
        id: "hero-main",
        type: "hero",
        visible: true,
        eyebrow: "The Little Style Club",
        headline: { lead: "Little Styles.", highlight: "Big Smiles." },
        body: "From everyday favourites to festive little statements, discover styles that make every childhood moment extra special.",
        primaryCta: { label: "Explore the Collection", href: "/shop" },
        secondaryCta: { label: "Discover New Arrivals", href: "/shop?sort=newest" },
        trust: [
          { icon: "sparkles", label: "Handpicked for Little Ones" },
          { icon: "message-circle", label: "Easy Ordering on WhatsApp" },
        ],
        messages: HERO_MESSAGES,
        image: null,
        theme: "blush",
        layout: "image-right",
      },
      {
        id: "categories",
        type: "category_showcase",
        visible: true,
        eyebrow: "Find their favourite",
        title: "Shop by category",
        limit: 6,
      },
      {
        id: "new-arrivals",
        type: "product_rail",
        visible: true,
        eyebrow: "Just in",
        title: "New arrivals",
        subtitle: "Fresh styles for playdates, parties and everything in between.",
        selection: { sort: "newest", limit: 8 },
        cta: { label: "View all new arrivals", href: "/shop?sort=newest" },
        layout: "carousel",
        theme: "ivory",
      },
      {
        id: "collections",
        type: "featured_collections",
        visible: true,
        eyebrow: "Curated for you",
        title: "Featured collections",
        items: [
          {
            title: "Festive Edit",
            caption: "Twirl-ready outfits for celebrations",
            href: "/collections/festive-edit",
            image: null,
            theme: "navy",
            art: "dress",
          },
          {
            title: "Everyday Play",
            caption: "Soft, easy pieces for busy days",
            href: "/collections/everyday-play",
            image: null,
            theme: "blush",
            art: "tee",
          },
          {
            title: "Little Ones",
            caption: "Gentle styles for the tiniest twinkles",
            href: "/collections/little-ones",
            image: null,
            theme: "gold",
            art: "romper",
          },
        ],
      },
      {
        id: "favourites",
        type: "product_rail",
        visible: true,
        eyebrow: "Handpicked",
        // Rename to "Bestsellers" only once it is driven by real sales data.
        title: "Our favourites",
        selection: { sort: "featured", limit: 8 },
        cta: { label: "Shop all styles", href: "/shop" },
        layout: "grid",
        theme: "ivory",
      },
      {
        id: "festive-banner",
        type: "promo_banner",
        visible: true,
        eyebrow: "The festive edit",
        title: "Dressed up for every celebration",
        body: "Shimmer, tulle and tiny bows — party looks they'll want to wear again and again.",
        cta: { label: "Explore the edit", href: "/collections/festive-edit" },
        image: null,
        theme: "navy",
      },
      {
        id: "assurances",
        type: "assurances",
        visible: true,
        title: "Shopping with Twinkle Kids",
        items: [
          {
            icon: "sparkles",
            title: "Thoughtfully curated",
            text: "Every style is chosen with comfort, charm and play in mind.",
          },
          {
            icon: "ruler",
            title: "Size guidance",
            text: "Age-based sizing with size charts on products where available.",
          },
          {
            icon: "message-circle",
            title: "Order your way",
            text: "Shop on the website or send your order to us on WhatsApp.",
          },
          {
            icon: "gift",
            title: "Made for gifting",
            text: "Sweet, occasion-ready picks for birthdays and festivals.",
          },
        ],
      },
      {
        id: "testimonials",
        type: "testimonials",
        visible: true,
        title: "Words from Twinkle families",
        items: [], // hidden until real, approved reviews are configured
      },
      {
        id: "contact",
        type: "contact",
        visible: true,
        title: "Need a hand choosing?",
        body: "Message us for sizing help or bulk and gifting orders.",
      },
    ],
  },
  commerce: { whatsappOrdering: false, guestCheckout: true, currency: "INR" },
  footer: {
    blurb:
      "A children's fashion boutique for adorable everyday outfits, festive looks and special occasion styles.",
    columns: [
      {
        title: "Shop",
        links: [
          { label: "Shop all", href: "/shop" },
          { label: "New arrivals", href: "/shop?sort=newest" },
          { label: "Wishlist", href: "/wishlist" },
          { label: "Shopping bag", href: "/bag" },
        ],
      },
      {
        title: "Customer care",
        links: [
          { label: "About us", href: "/about" },
          { label: "Contact us", href: "/contact" },
          { label: "My account", href: "/account" },
        ],
      },
    ],
    policies: [],
    social: [],
  },
  contact: { email: null, phone: null, whatsapp: null, address: null, hours: null },
  pages: {
    "size-guide": { title: "Size guide", summary: "How to choose the right size." },
    shipping: { title: "Shipping", summary: "Delivery information." },
    returns: { title: "Returns & exchanges", summary: "Our returns and exchange policy." },
    contact: { title: "Contact us", summary: "How to reach the Twinkle Kids team." },
    "privacy-policy": { title: "Privacy policy", summary: "How we handle your information." },
    terms: { title: "Terms of service", summary: "Terms for using this website." },
  },
};
