import { Inter } from 'next/font/google';
import { RootProvider } from 'fumadocs-ui/provider';
import './global.css';
import { metadata as siteMetadata } from './layout.config';
import { StaticSearchDialog } from '@/components/search-dialog';

export const metadata = siteMetadata;

const inter = Inter({
  subsets: ['latin'],
  weight: ['200', '300', '400', '500'],
  display: 'swap',
  variable: '--font-inter',
});

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable}`}>
      <body className="flex min-h-screen flex-col font-sans">
        <RootProvider
          search={{
            SearchDialog: StaticSearchDialog,
          }}
        >
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
