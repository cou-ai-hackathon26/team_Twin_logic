import { useSyncExternalStore } from 'react'

/** Teacher interface language. Navigation, page titles and the main buttons are translated; details stay English. */
export type UiLang = 'en' | 'bn'
const KEY = 'pb-ui-lang'
const listeners = new Set<() => void>()
const read = (): UiLang => (localStorage.getItem(KEY) === 'bn' ? 'bn' : 'en')

export function setUiLang(l: UiLang) {
  localStorage.setItem(KEY, l)
  document.documentElement.lang = l
  listeners.forEach((f) => f())
}

export function useUiLang(): UiLang {
  return useSyncExternalStore(
    (f) => (listeners.add(f), () => listeners.delete(f)),
    read,
    () => 'en',
  )
}

const BN: Record<string, string> = {
  // navigation
  Teaching: 'পাঠদান',
  'AI lab': 'এআই ল্যাব',
  Account: 'অ্যাকাউন্ট',
  'My classes': 'আমার শ্রেণি',
  Dashboard: 'ড্যাশবোর্ড',
  'New assessment': 'নতুন মূল্যায়ন',
  'Review queue': 'যাচাইয়ের তালিকা',
  Passages: 'পাঠ্যাংশ',
  'Grapheme engine': 'বর্ণ বিশ্লেষণ',
  Benchmark: 'মূল্যায়ন ফলাফল',
  Settings: 'সেটিংস',
  Home: 'হোম',
  Assess: 'মূল্যায়ন',
  Review: 'যাচাই',
  Engine: 'বিশ্লেষণ',
  Bench: 'ফলাফল',
  'Search…': 'খুঁজুন…',
  // page titles and subtitles
  'Your classes': 'আপনার শ্রেণিগুলো',
  "Open a class to see each child's marks and the class's weak patterns.": 'শ্রেণি খুললে প্রতিটি শিশুর নম্বর ও শ্রেণির দুর্বল দিকগুলো দেখবেন।',
  'Choose the child and a passage, then hand the device to the child.': 'শিশু ও পাঠ্যাংশ বেছে নিন, তারপর যন্ত্রটি শিশুর হাতে দিন।',
  'AI marks are suggestions. Check each reading, change any mark, then finalise it.': 'এআই-এর নম্বর শুধু পরামর্শ। প্রতিটি পড়া যাচাই করুন, দরকারে বদলান, তারপর চূড়ান্ত করুন।',
  'Passage bank': 'পাঠ্যাংশ ভান্ডার',
  'Bangla grapheme engine': 'বাংলা বর্ণ বিশ্লেষণ',
  // buttons
  'Start an assessment': 'মূল্যায়ন শুরু করুন',
  'New reading': 'নতুন পড়া',
  'Assess a child': 'শিশুর মূল্যায়ন',
  'Add students': 'শিক্ষার্থী যোগ',
  Assign: 'কাজ দিন',
  Export: 'এক্সপোর্ট',
  Report: 'রিপোর্ট',
  Edit: 'সম্পাদনা',
}

/** Translate a known interface string; anything unknown is returned unchanged. */
export function tr(lang: UiLang, s: string): string {
  return lang === 'bn' ? (BN[s] ?? s) : s
}

export const useT = () => {
  const lang = useUiLang()
  return (s: string) => tr(lang, s)
}
