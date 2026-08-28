"use client";
import type { ComponentProps } from "react";
import { useSearchContext } from "fumadocs-ui/contexts/search";
import { useI18n } from "fumadocs-ui/contexts/i18n";
import { cn } from "fumadocs-ui/utils/cn";
import {
  type ButtonProps,
  buttonVariants,
} from "fumadocs-ui/components/ui/button";

function SearchIcon(props: ComponentProps<"svg">) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

interface SearchToggleProps
  extends Omit<ComponentProps<"button">, "color">,
    ButtonProps {
  hideIfDisabled?: boolean;
}

export function SearchToggle({
  hideIfDisabled,
  size = "icon",
  color = "ghost",
  ...props
}: SearchToggleProps) {
  const { setOpenSearch, enabled } = useSearchContext();
  if (hideIfDisabled && !enabled) return null;

  return (
    <button
      type="button"
      className={cn(
        buttonVariants({
          size,
          color,
        }),
        props.className
      )}
      data-search=""
      aria-label="Open Search"
      onClick={() => {
        setOpenSearch(true);
      }}
    >
      <SearchIcon className="p-px" />
    </button>
  );
}

export function LargeSearchToggle({
  hideIfDisabled,
  ...props
}: ComponentProps<"button"> & {
  hideIfDisabled?: boolean;
}) {
  const { enabled, hotKey, setOpenSearch } = useSearchContext();
  const { text } = useI18n();
  if (hideIfDisabled && !enabled) return null;

  return (
    <button
      type="button"
      data-search-full=""
      {...props}
      className={cn(
        "inline-flex items-center gap-2 rounded-none border bg-white dark:bg-transparent p-1.5 ps-2 text-sm text-[#757575] transition-colors hover:bg-fd-accent hover:text-fd-accent-foreground",
        props.className
      )}
      onClick={() => {
        setOpenSearch(true);
      }}
    >
      <SearchIcon className="size-4" strokeWidth={1} />
      {text.search}
      <div className="ms-auto inline-flex gap-0">
        {hotKey.map((k, i) => (
          <kbd
            key={i}
            className="rounded-md border-0 bg-transparent text-[#757575] px-1.5"
          >
            {k.display}
          </kbd>
        ))}
      </div>
    </button>
  );
}
