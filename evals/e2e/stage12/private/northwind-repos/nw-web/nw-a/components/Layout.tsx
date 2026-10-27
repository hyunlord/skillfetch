import Head from 'next/head'
import { ReactNode } from 'react'

type Props = { children: ReactNode; title?: string }

export default function Layout({ children, title = 'Northwind' }: Props) {
  return (
    <>
      <Head><title>{title}</title></Head>
      <nav style={{ padding: '16px', borderBottom: '1px solid #eee' }}>
        <a href="/" style={{ marginRight: '16px', color: '#0066cc' }}>Home</a>
      </nav>
      <main style={{ padding: '16px' }}>{children}</main>
    </>
  )
}
