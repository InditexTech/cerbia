import { source } from '@/lib/source';
import {
  DocsPage,
  DocsBody,
  DocsDescription,
  DocsTitle,
} from 'fumadocs-ui/page';
import { notFound } from 'next/navigation';
import { createRelativeLink } from 'fumadocs-ui/mdx';
import { useMDXComponents } from '@/mdx-components';

const getNormalizedLink = (page: NonNullable<ReturnType<typeof source.getPage>>) => {
  const RelativeLink = createRelativeLink(source, page);

  return function NormalizedLink(props: React.ComponentProps<'a'>) {
    let href = props.href;

    if (
      href &&
      !href.startsWith('/') &&
      !href.startsWith('#') &&
      !href.startsWith('.') &&
      !href.includes(':') &&
      (href.includes('.mdx') || href.includes('.md'))
    ) {
      href = `./${href}`;
    }

    return <RelativeLink {...props} href={href} />;
  };
};

export default async function Page(props: {
  params: Promise<{ slug?: string[] }>;
}) {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  const MDX = page.data.body;
  const NormalizedLink = getNormalizedLink(page);

  return (
    <DocsPage toc={page.data.toc} full={page.data.full}>
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDX components={useMDXComponents({
          a: NormalizedLink
        })} />
      </DocsBody>
    </DocsPage>
  );
}

export async function generateStaticParams() {
  return source.generateParams();
}

export async function generateMetadata(props: {
  params: Promise<{ slug?: string[] }>;
}) {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  return {
    title: page.data.title,
    description: page.data.description,
  };
}
