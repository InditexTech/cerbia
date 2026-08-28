import { docs, meta } from '@/.source';
import { createMDXSource, resolveFiles } from 'fumadocs-mdx';
import { loader } from 'fumadocs-core/source';

const mdxSource = createMDXSource(docs, meta);
Object.assign(mdxSource, { files: resolveFiles({ docs, meta }) });

export const source = loader({
  baseUrl: '/docs',
  source: mdxSource,
});
