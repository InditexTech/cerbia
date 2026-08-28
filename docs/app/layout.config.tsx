import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import Image from 'next/image';
import Logo from '@/public/logo.png';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <>
        <Image
          alt="CerbIA Logo"
          src={Logo}
          width={32}
          height={32}
          className="w-8 h-8"
          aria-label="CerbIA"
        />
        <span className="font-medium ml-2">CerbIA</span>
      </>
    ),
    transparentMode: 'top',
  },
  links: [],
  githubUrl: 'https://github.com/inditextech/cerbia',
};

export const metadata = {
  metadataBase: new URL('https://inditextech.github.io/cerbia'),
  title: {
    template: '%s | CerbIA',
    default: 'CerbIA',
  },
  description: "CerbIA composes security gates around AI agents' inputs and outputs.",
  icons: {
    icon: [
      { url: '/cerbia/favicon.png', type: 'image/png' },
    ],
    shortcut: ['/cerbia/favicon.png'],
    apple: [
      { url: '/cerbia/favicon.png', type: 'image/png' },
    ],
  },
};
