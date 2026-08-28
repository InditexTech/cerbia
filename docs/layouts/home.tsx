"use client";
import React, { type HTMLAttributes, useState, useMemo } from "react";
import { cn } from "fumadocs-ui/utils/cn";
import { NavProvider, useNav } from "fumadocs-ui/contexts/layout";
import { LargeSearchToggle, SearchToggle } from "@/components/layout/search-toggle";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import Link from "fumadocs-core/link";
import { buttonVariants } from "fumadocs-ui/components/ui/button";

function GithubIcon(props: React.ComponentProps<"svg">) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

function MenuIcon({ open, ...props }: React.ComponentProps<"svg"> & { open: boolean }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props} className={cn("transition-transform duration-300", open ? "rotate-180" : "", props.className)}>
      {open ? (
        <>
          <line x1="18" x2="6" y1="6" y2="18" />
          <line x1="6" x2="18" y1="6" y2="18" />
        </>
      ) : (
        <>
          <line x1="4" x2="20" y1="12" y2="12" />
          <line x1="4" x2="20" y1="6" y2="6" />
          <line x1="4" x2="20" y1="18" y2="18" />
        </>
      )}
    </svg>
  );
}

export interface NavOptions {
  enabled?: boolean;
  component?: React.ReactNode;
  title?: React.ReactNode;
  url?: string;
  children?: React.ReactNode;
  transparentMode?: "always" | "top" | "none";
  enableHoverToOpen?: boolean;
}

export interface BaseLayoutProps {
  themeSwitch?: {
    enabled?: boolean;
    component?: React.ReactNode;
    mode?: "light-dark" | "light-dark-system";
  };
  searchToggle?: Partial<{
    enabled: boolean;
    components: Partial<{
      sm: React.ReactNode;
      lg: React.ReactNode;
    }>;
  }>;
  githubUrl?: string;
  links?: { text: string; url: string; active?: string }[];
  nav?: Partial<NavOptions>;
  children?: React.ReactNode;
}

export function HomeLayout(
  props: BaseLayoutProps & HTMLAttributes<HTMLElement>
) {
  const {
    nav = {},
    links = [],
    githubUrl,
    themeSwitch,
    searchToggle,
    ...rest
  } = props;

  return (
    <NavProvider transparentMode={nav?.transparentMode}>
      <main
        id="nd-home-layout"
        {...rest}
        className={cn("flex flex-1 flex-col pt-[84px]", rest.className)}
      >
        <Header
          links={links}
          nav={nav}
          themeSwitch={themeSwitch}
          searchToggle={searchToggle}
          githubUrl={githubUrl}
        />
        {props.children}
      </main>
    </NavProvider>
  );
}

function Header({
  nav = {},
  links = [],
  githubUrl,
  themeSwitch,
  searchToggle,
}: BaseLayoutProps) {
  const { isTransparent } = useNav();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header
      id="nd-nav"
      className={cn(
        "fixed top-[var(--fd-banner-height,0px)] z-40 box-content backdrop-blur-lg max-w-fd-container -translate-x-1/2 border-b transition-colors lg:mt-[16px] lg:[--fd-padding:1rem] lg:rounded-none lg:border shadow-none",
        !isTransparent || mobileMenuOpen ? "bg-white/50 dark:bg-black/50" : "bg-transparent"
      )}
      style={{
        width:
          "calc(100% - 2 * var(--fd-padding,0px) - var(--removed-body-scroll-bar-size,0px))",
        left: "calc(50% - var(--removed-body-scroll-bar-size,0px) / 2)",
      }}
    >
      <div className="flex h-[60px] w-full items-center px-[24px] lg:h-[60px]">
        <Link
          href={nav.url ?? "/"}
          className="inline-flex items-center gap-2.5 !font-light"
        >
          {nav.title}
        </Link>
        {nav.children}

        {/* Desktop Links */}
        <ul className="flex flex-row items-center gap-2 px-6 max-sm:hidden">
          {links.map((item, i) => (
            <li key={i}>
              <Link
                href={item.url}
                className="font-light !text-black dark:!text-white text-[13px] hover:!text-[#757575] hover:!font-medium px-2 py-2 transition-colors"
              >
                {item.text}
              </Link>
            </li>
          ))}
        </ul>

        {/* Toggles (Search, Theme) */}
        <div className="flex flex-row items-center justify-end gap-[32px] flex-1 mr-[32px]">
          <div className="lg:hidden">
            {searchToggle?.components?.sm || <SearchToggle className="p-2 lg:hidden" hideIfDisabled />}
          </div>
          <div className="max-lg:hidden w-full max-w-[240px]">
            {searchToggle?.components?.lg || <LargeSearchToggle className="w-full max-w-[240px]" hideIfDisabled />}
          </div>
          <div className="max-lg:hidden">
            {themeSwitch?.component || <ThemeToggle mode={themeSwitch?.mode} />}
          </div>
        </div>

        {/* Desktop Icons + Mobile Menu */}
        <ul className="flex flex-row items-center ms-auto lg:ms-0">
          {githubUrl ? (
            <li className="max-lg:hidden flex items-center">
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="font-light text-black dark:text-white bg-transparent shadow-none text-[13px] dark:hover:!text-[#454545] hover:!text-[#757575] hover:!font-medium hover:!text-black hover:!bg-transparent !w-auto inline-flex items-center gap-1 p-2"
                aria-label="GitHub"
              >
                <GithubIcon className="text-black dark:text-white hover:text-[#757575] dark:hover:text-[#bfbfbf]" />
              </a>
            </li>
          ) : null}

          <li className="lg:hidden relative">
            <button
              aria-label="Toggle Menu"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={cn(buttonVariants({ size: "icon", color: "ghost" }), "group -me-2")}
            >
              <MenuIcon open={mobileMenuOpen} className="!size-5.5" />
            </button>
          </li>
        </ul>
      </div>

      {/* Mobile Menu Content */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-[60px] left-0 right-0 bg-background border-b border-border shadow-lg p-4 animate-in slide-in-from-top-2">
          <div className="flex flex-col gap-4">
            {links.map((item, i) => (
              <Link
                key={i}
                href={item.url}
                onClick={() => setMobileMenuOpen(false)}
                className="font-light text-[16px] text-foreground hover:text-muted-foreground"
              >
                {item.text}
              </Link>
            ))}
          </div>
          <div className="-ms-1.5 flex flex-row items-center gap-1.5 mt-4 pt-4 border-t border-border">
            {githubUrl ? (
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="-me-1.5 p-2 text-foreground hover:text-muted-foreground"
                aria-label="GitHub"
              >
                <GithubIcon />
              </a>
            ) : null}
            <div role="separator" className="flex-1" />
            {themeSwitch?.component || <ThemeToggle mode={themeSwitch?.mode} />}
          </div>
        </div>
      )}
    </header>
  );
}
