import { useEffect } from 'react'

const BASE = 'ForgeFlow'

/**
 * Sets `document.title` for the current route and restores the previous title
 * on unmount. Because ForgeFlow is a client-rendered SPA, this is what gives
 * each route a distinct, meaningful tab/title for users and (JS-executing)
 * crawlers. Pass a page-specific string; it is suffixed with the brand.
 */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    const previous = document.title
    document.title = title ? `${title} · ${BASE}` : BASE
    return () => {
      document.title = previous
    }
  }, [title])
}
