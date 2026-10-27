import en from '../locales/en.json'
import ko from '../locales/ko.json'

type Messages = Record<string, any>
const bundles: Record<string, Messages> = { en, ko }

export function t(key: string, locale: string = 'en'): string {
  const parts = key.split('.')
  let node: any = bundles[locale] ?? bundles['en']
  for (const p of parts) {
    node = node?.[p]
  }
  return typeof node === 'string' ? node : key
}
