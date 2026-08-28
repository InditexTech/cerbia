import { useMemo } from 'react';
import type { PageTree } from "fumadocs-core/server";
import type { HTMLAttributes, ReactNode, ComponentProps } from 'react';
import { cn } from 'fumadocs-ui/utils/cn';
import { buttonVariants } from 'fumadocs-ui/components/ui/button';
import {
  Sidebar,
  SidebarCollapseTrigger,
  SidebarContent,
  SidebarContentMobile,
  SidebarFooter,
  SidebarHeader,
  SidebarPageTree,
  SidebarTrigger,
  SidebarViewport,
  SidebarItem,
  SidebarFolder,
  SidebarFolderLink,
  SidebarFolderTrigger,
  SidebarFolderContent,
} from 'fumadocs-ui/components/layout/sidebar';
import { RootToggle } from 'fumadocs-ui/components/layout/root-toggle';
import { BaseLinkItem } from 'fumadocs-ui/layouts/links';
import { LanguageToggle, LanguageToggleText } from 'fumadocs-ui/components/layout/language-toggle';
import { CollapsibleControl, LayoutBody, LayoutTabs, Navbar } from 'fumadocs-ui/layouts/docs-client';
import { TreeContextProvider } from 'fumadocs-ui/contexts/tree';
import { ThemeToggle } from '@/components/layout/theme-toggle';
import { NavProvider } from 'fumadocs-ui/contexts/layout';
import Link from 'fumadocs-core/link';
import { LargeSearchToggle, SearchToggle } from '@/components/layout/search-toggle';
import { getSidebarTabs } from 'fumadocs-ui/utils/get-sidebar-tabs';
import { getLinks, type BaseLayoutProps, type LinkItemType } from './shared';

function LanguagesIcon(props: ComponentProps<"svg">) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/></svg>
  )
}

function SidebarIcon(props: ComponentProps<"svg">) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>
  )
}

export interface DocsLayoutProps extends BaseLayoutProps {
  tree: PageTree.Root;
  sidebar?: any;
  tabMode?: 'top' | 'auto';
  containerProps?: HTMLAttributes<HTMLDivElement>;
}

export function DocsLayout({
  nav: { transparentMode, ...nav } = {},
  sidebar: { tabs: sidebarTabs, enabled: sidebarEnabled = true, ...sidebarProps } = {},
  searchToggle = {},
  themeSwitch = {},
  tabMode = 'auto',
  i18n = false,
  children,
  ...props
}: DocsLayoutProps) {

  const tabs = useMemo(() => {
    if (Array.isArray(sidebarTabs)) return sidebarTabs;
    if (typeof sidebarTabs === 'object') return getSidebarTabs(props.tree, sidebarTabs);
    if (sidebarTabs !== false) return getSidebarTabs(props.tree);
    return [];
  }, [sidebarTabs, props.tree]);

  const links = getLinks(props.links ?? [], props.githubUrl);

  const sidebarVariables = cn('md:[--fd-sidebar-width:268px] lg:[--fd-sidebar-width:290px]');

  function sidebar() {
    const { footer, banner, collapsible = true, component, components, defaultOpenLevel, prefetch, ...rest } = sidebarProps;
    if (component) return component;

    const iconLinks = links.filter((item) => item.type === 'icon');

    const viewport = (
      <SidebarViewport>
        {links.filter((v) => v.type !== 'icon').map((item, i, list) => (
          <SidebarLinkItem key={i} item={item} className={cn(i === list.length - 1 && 'mb-4')} />
        ))}
        <SidebarPageTree components={components} />
      </SidebarViewport>
    );

    const weaveFooter = (
      <div className="flex items-center justify-end">
        <div className="flex items-center flex-1 empty:hidden">
          {iconLinks.map((item, i) => (
            <BaseLinkItem
              key={i}
              item={item}
              className={cn(
                buttonVariants({ size: "icon", color: "ghost" }),
                "text-fd-muted-foreground md:[&_svg]:size-4.5"
              )}
              aria-label={item.label}
            >
              {item.icon}
            </BaseLinkItem>
          ))}
        </div>
        {i18n ? (
          <LanguageToggle className="me-1.5">
            <LanguagesIcon className="size-4.5" />
            <LanguageToggleText className="md:hidden" />
          </LanguageToggle>
        ) : null}
        <ThemeToggle className="p-0" mode={themeSwitch?.mode} />
      </div>
    );

    const mobile = (
      <SidebarContentMobile {...rest}>
        <SidebarHeader>
          <div className="flex text-fd-muted-foreground items-center gap-1.5">
            <div className="flex flex-1">
              {iconLinks.map((item, i) => (
                <BaseLinkItem key={i} item={item} className={cn(buttonVariants({ size: 'icon-sm', color: 'ghost', className: 'p-2' }))} aria-label={item.label}>
                  {item.icon}
                </BaseLinkItem>
              ))}
            </div>
            {i18n ? (
              <LanguageToggle>
                <LanguagesIcon className="size-4.5" />
                <LanguageToggleText />
              </LanguageToggle>
            ) : null}
            {themeSwitch.enabled !== false && (themeSwitch.component ?? <ThemeToggle className="p-0" mode={themeSwitch.mode} />)}
            <SidebarTrigger className={cn(buttonVariants({ color: 'ghost', size: 'icon-sm', className: 'p-2' }))}>
              <SidebarIcon />
            </SidebarTrigger>
          </div>
          {tabs.length > 0 && <RootToggle options={tabs} />}
          {banner}
        </SidebarHeader>
        {viewport}
        <SidebarFooter className="empty:hidden">
          {footer}
        </SidebarFooter>
      </SidebarContentMobile>
    );

    const content = (
      <SidebarContent {...rest} className={cn("bg-white dark:bg-black", rest.className)}>
        <SidebarHeader>
          <div className="flex max-md:hidden">
            <Link href={nav.url ?? '/'} className="inline-flex text-[15px] items-center gap-2.5 font-medium me-auto">
              {nav.title}
            </Link>
            {nav.children}
            {collapsible && (
              <SidebarCollapseTrigger className={cn(buttonVariants({ color: 'ghost', size: 'icon-sm' }), "ms-auto mb-auto text-fd-muted-foreground max-md:hidden")}>
                <SidebarIcon strokeWidth={1} />
              </SidebarCollapseTrigger>
            )}
          </div>
          {tabs.length > 0 ? <RootToggle options={tabs} /> : null}
          {searchToggle.enabled !== false && (searchToggle.components?.lg ?? <LargeSearchToggle hideIfDisabled className="max-md:hidden" />)}
          {banner}
        </SidebarHeader>
        {viewport}
        <SidebarFooter>
          {weaveFooter}
          {footer}
        </SidebarFooter>
      </SidebarContent>
    );

    return (
      <Sidebar defaultOpenLevel={defaultOpenLevel} prefetch={prefetch} Mobile={mobile} Content={
        <>
          {collapsible && <CollapsibleControl />}
          {content}
        </>
      } />
    );
  }

  return (
    <TreeContextProvider tree={props.tree}>
      <NavProvider transparentMode={transparentMode}>
        {nav.enabled !== false && (nav.component ?? (
          <Navbar className="h-(--fd-nav-height) on-root:[--fd-nav-height:56px] md:on-root:[--fd-nav-height:0px] md:hidden">
            <Link href={nav.url ?? '/'} className="inline-flex items-center gap-2.5 font-semibold">
              {nav.title}
            </Link>
            <div className="flex-1">{nav.children}</div>
            {searchToggle.enabled !== false && (searchToggle.components?.sm ?? <SearchToggle className="p-2" hideIfDisabled />)}
            {sidebarEnabled && (
              <SidebarTrigger className={cn(buttonVariants({ color: 'ghost', size: 'icon-sm', className: 'p-2' }))}>
                <SidebarIcon />
              </SidebarTrigger>
            )}
          </Navbar>
        ))}
        <LayoutBody {...props.containerProps} className={cn('md:[&_#nd-page_article]:pt-12 xl:[--fd-toc-width:290px] xl:[&_#nd-page_article]:px-8', sidebarEnabled && sidebarVariables, props.containerProps?.className)}>
          {sidebarEnabled && sidebar()}
          {tabMode === 'top' && tabs.length > 0 && (
            <LayoutTabs options={tabs} className="sticky top-[calc(var(--fd-nav-height)+var(--fd-tocnav-height))] z-10 bg-fd-background border-b px-6 pt-3 xl:px-8 max-md:hidden" />
          )}
          {children}
        </LayoutBody>
      </NavProvider>
    </TreeContextProvider>
  );
}

function SidebarLinkItem({ item, ...props }: { item: LinkItemType; className?: string }) {
  if (item.type === 'menu')
    return (
      <SidebarFolder {...props}>
        {item.url ? (
          <SidebarFolderLink href={item.url} external={item.external}>
            {item.icon}
            {item.text}
          </SidebarFolderLink>
        ) : (
          <SidebarFolderTrigger>
            {item.icon}
            {item.text}
          </SidebarFolderTrigger>
        )}
        <SidebarFolderContent>
          {item.items.map((child, i) => (
            <SidebarLinkItem key={i} item={child} />
          ))}
        </SidebarFolderContent>
      </SidebarFolder>
    );

  if (item.type === 'custom') return <div {...props}>{item.children}</div>;

  return (
    <SidebarItem href={item.url} icon={item.icon} external={item.external} {...props}>
      {item.text}
    </SidebarItem>
  );
}
