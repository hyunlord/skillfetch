import Layout from '../components/Layout'
import { t } from '../lib/i18n'
import { track } from '../lib/analytics'
import { useEffect } from 'react'

export default function ProductsPage() {
  useEffect(() => {
    track('products_view', { source: 'nav' })
  }, [])

  return (
    <Layout title={t('products.page_title')}>
      <h1 style={{
        color: 'var(--nw-color-text)',
        marginBottom: 'var(--nw-spacing-lg)',
        fontSize: 'var(--nw-font-size-lg)'
      }}>
        {t('products.heading')}
      </h1>
      <div style={{
        padding: 'var(--nw-spacing-md)',
        backgroundColor: 'var(--nw-color-bg-secondary)',
        borderRadius: 'var(--nw-radius-md)',
        border: '1px solid var(--nw-color-border)'
      }}>
        <p style={{
          color: 'var(--nw-color-text-secondary)',
          fontSize: 'var(--nw-font-size-md)'
        }}>
          {t('products.empty_state')}
        </p>
      </div>
    </Layout>
  )
}
