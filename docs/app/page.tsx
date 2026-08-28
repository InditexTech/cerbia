import Link from 'next/link';
import { HomeLayout } from '@/layouts/home';
import { baseOptions } from '@/app/layout.config';
import React from 'react';
import { SearchToggle, LargeSearchToggle } from '@/components/layout/search-toggle';
import { ThemeToggle } from '@/components/layout/theme-toggle';

export default function HomePage() {
  return (
    <HomeLayout
      {...baseOptions}
      links={[{ text: 'DOCUMENTATION', url: '/docs', active: 'nested-url' }]}
      themeSwitch={{
        component: <ThemeToggle mode="light-dark" />
      }}
      searchToggle={{
        components: {
          sm: <SearchToggle hideIfDisabled />,
          lg: <LargeSearchToggle hideIfDisabled className="w-full max-w-[240px] max-lg:hidden" />
        }
      }}
    >
      <div className="flex flex-col min-h-screen text-foreground relative z-[2]">
        <div className="flex flex-col justify-start items-center w-full">
          <Hero />
          <UsageModes />
          <Architecture />
          <Features />
          <GetStarted />
          <OpenSource />
        </div>
      </div>
      <End />
    </HomeLayout>
  );
}

function Hero() {
  return (
    <div className="max-w-[800px] relative z-[2] flex flex-col justify-center items-center px-6 pt-[56px] text-center md:px-12 md:pt-[96px] max-lg:overflow-hidden">
      <h1 className="mb-[32px] text-[48px] leading-[56px] font-light md:hidden">
        Security gates for AI agents' inputs and outputs
      </h1>
      <h1 className="mb-[32px] max-md:hidden">
        <span className="text-[48px] leading-[56px] font-light">
          Security gates for AI agents' inputs and outputs
        </span>
      </h1>
      <p className="mb-8 font-light leading-[28px] text-muted-foreground md:text-[20px]">
        CerbIA is a Python library and CLI for reusable security gates. Check prompts, files, instructions, configurations, and agent inputs/outputs before application, CI/CD, or local use.
      </p>
      <div className="w-full flex justify-center items-center gap-3 max-md:mx-auto flex-wrap">
        <LinkButton href="https://github.com/inditextech/cerbia" external variant="outline">
          View on GitHub
        </LinkButton>
        <LinkButton href="/docs" variant="default" style="main">
          Read the documentation
        </LinkButton>
      </div>
    </div>
  );
}

function UsageModes() {
  return (
    <div className="max-w-[1200px] w-full mt-[128px] flex flex-col px-6">
      <div className="col-span-2 mb-[40px]">
        <div className="text-center text-[32px] leading-[40px] font-light uppercase">
          Use it where you work
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-[24px]">
        <div className="bg-background border border-border p-6 lg:p-8 flex flex-col gap-3">
          <h3 className="text-[20px] font-medium leading-[28px]">Python Library</h3>
          <p className="text-[16px] text-muted-foreground font-light leading-[24px]">
            Integrate directly into your application code with a native Python API for evaluating agent interactions in real-time.
          </p>
        </div>
        <div className="bg-background border border-border p-6 lg:p-8 flex flex-col gap-3">
          <h3 className="text-[20px] font-medium leading-[28px]">Command Line</h3>
          <p className="text-[16px] text-muted-foreground font-light leading-[24px]">
            Scan files, inputs, and configurations locally with the <code className="font-mono text-[13px]">cerbia</code> CLI before deploying.
          </p>
        </div>
        <div className="bg-background border border-border p-6 lg:p-8 flex flex-col gap-3">
          <h3 className="text-[20px] font-medium leading-[28px]">CI/CD Pipelines</h3>
          <p className="text-[16px] text-muted-foreground font-light leading-[24px]">
            Automate checks in your deployment pipelines using the same CLI and declarative YAML configuration.
          </p>
        </div>
      </div>
    </div>
  );
}

function Architecture() {
  return (
    <div className="max-w-[1200px] w-full grid grid-cols-1 md:grid-cols-2 gap-[80px] px-6 pt-[64px] md:pt-[128px]">
      <div className="md:hidden flex justify-center items-center">
        <div className="flex flex-col gap-4 w-full max-w-[300px]">
           <div className="p-4 border border-border text-center font-light uppercase bg-muted/20">Loader</div>
           <div className="text-center text-muted-foreground font-light">↓</div>
           <div className="p-4 border border-border text-center font-light uppercase bg-muted/20">Preprocessor</div>
           <div className="text-center text-muted-foreground font-light">↓</div>
           <div className="p-4 border border-border text-center font-light uppercase bg-muted/20">Scanner</div>
           <div className="text-center text-muted-foreground font-light">↓</div>
           <div className="p-4 border border-border bg-black text-white dark:bg-white dark:text-black text-center font-light uppercase">Aggregator</div>
        </div>
      </div>
      <div className="flex flex-col justify-center">
        <h2 className="font-light text-[32px] leading-[40px] uppercase text-left">
          Declarative Evaluation
        </h2>
        <div className="mt-[16px] font-light text-[20px] leading-[28px] text-left text-muted-foreground">
          YAML-first reviewable, versionable, and distributable configuration. A pipeline evaluates content through four composable stages, returning an aggregated risk verdict.
        </div>
        <div className="mt-[32px] grid grid-cols-1 gap-[24px]">
          <div>
            <h3 className="text-[18px] font-medium leading-[24px]">1. Load</h3>
            <p className="text-[16px] font-light text-muted-foreground leading-[22px]">Extract content from inline text or file inputs.</p>
          </div>
          <div>
            <h3 className="text-[18px] font-medium leading-[24px]">2. Normalize</h3>
            <p className="text-[16px] font-light text-muted-foreground leading-[22px]">Clean and normalize the extracted data prior to inspection.</p>
          </div>
          <div>
            <h3 className="text-[18px] font-medium leading-[24px]">3. Inspect</h3>
            <p className="text-[16px] font-light text-muted-foreground leading-[22px]">Layered detection using pattern-based scanners and optional local ML integrations.</p>
          </div>
          <div>
            <h3 className="text-[18px] font-medium leading-[24px]">4. Decide</h3>
            <p className="text-[16px] font-light text-muted-foreground leading-[22px]">Compute a final risk score and return a definitive block or allow verdict.</p>
          </div>
        </div>
      </div>
      <div className="hidden md:flex justify-center items-center">
        <div className="flex flex-col gap-4 w-full max-w-[300px]">
           <div className="p-4 border border-border text-center font-light uppercase bg-muted/20">Loader</div>
           <div className="text-center text-muted-foreground font-light">↓</div>
           <div className="p-4 border border-border text-center font-light uppercase bg-muted/20">Preprocessor</div>
           <div className="text-center text-muted-foreground font-light">↓</div>
           <div className="p-4 border border-border text-center font-light uppercase bg-muted/20">Scanner</div>
           <div className="text-center text-muted-foreground font-light">↓</div>
           <div className="p-4 border border-black bg-black text-white dark:bg-white dark:text-black dark:border-white text-center font-light uppercase">Aggregator</div>
        </div>
      </div>
    </div>
  );
}

function Features() {
  return (
    <div className="max-w-[1200px] w-full mt-[128px] flex flex-col px-6">
      <div className="mb-[40px] flex flex-col items-center">
        <h2 className="text-center text-[32px] leading-[40px] font-light uppercase">
          Extend it. Run it anywhere
        </h2>
        <p className="mt-[16px] text-center text-[20px] leading-[28px] font-light text-muted-foreground max-w-[800px]">
                Define custom language and pattern support alongside pipeline components once. Configure them declaratively in YAML, then run the same gate consistently across applications, environments, and CI/CD pipelines.
        </p>
      </div>
      <div className="w-full grid grid-cols-1 gap-[24px] md:grid-cols-2">
        <div className="bg-background col-span-1 md:col-span-2 border border-border p-8 lg:p-12">
          <div className="max-w-[800px]">
            <h3 className="text-[24px] font-light leading-[32px] mb-4">Custom Pipeline Components</h3>
            <p className="text-[18px] text-muted-foreground font-light leading-[28px] mb-8">
              Extend CerbIA with your own logic without forking the codebase. Configure custom loaders, preprocessors, scanners, and score aggregators using fully-qualified Python class paths and initialization arguments.
            </p>
            <div className="w-full p-4 border border-border font-mono text-[13px] bg-muted/30 overflow-x-auto whitespace-pre text-foreground">
{`scanners:
  - scanner: your_package.components.CompanyPolicyScanner
    init_args:
      blocked_phrase: "internal only"`}
            </div>
          </div>
        </div>
        <div className="bg-background border border-border p-6 lg:p-8 flex flex-col gap-3">
            <h3 className="text-[20px] font-medium leading-[28px]">Language & Pattern Packs</h3>
            <p className="text-[16px] text-muted-foreground font-light leading-[24px]">
              Register language-specific regular expressions for built-in scanners using ISO-639-1 language codes and the <code className="font-mono text-[13px]">@i18n_pattern</code> decorator. Built-in packs support English, Spanish, and Galician.
            </p>
        </div>
        <div className="bg-background border border-border p-6 lg:p-8 flex flex-col gap-3">
            <h3 className="text-[20px] font-medium leading-[28px]">Layered Detection</h3>
            <p className="text-[16px] text-muted-foreground font-light leading-[24px]">
              Combine fast pattern-based scanners for suspicious instructions, secrets, PII, URLs, and hidden text, with optional local ML-backed integrations for selected scenarios.
            </p>
        </div>
      </div>
    </div>
  );
}

function GetStarted() {
  return (
    <div className="max-w-[1200px] w-full flex flex-col justify-center items-center gap-4 px-6 pt-[128px]">
      <div>
        <h2 className="font-light text-[32px] leading-[40px] uppercase text-center">
          Start scanning in three steps
        </h2>
        <div className="mt-[16px] font-light text-[20px] leading-[28px] text-center">
          Evaluate inputs and outputs with declarative YAML configs.
        </div>
      </div>
      <div className="w-full grid grid-cols-1 gap-[80px] md:grid-cols-3 mt-12 overflow-hidden">
        <div className="bg-background flex flex-col gap-3 justify-between items-start">
          <div className="flex flex-col gap-3 w-full">
            <div className="inline-flex size-7 text-[16px] leading-[20px] font-light items-center justify-center rounded-full bg-black text-white dark:bg-white dark:text-black">1</div>
            <h3 className="text-[20px] leading-[28px] font-light">Install CerbIA</h3>
            <p className="text-[16px] leading-[22px] text-muted-foreground font-light md:min-h-[72px]">
              Install the package with CLI support.
            </p>
            <div className="w-full p-4 border border-border font-mono text-sm bg-muted/30 overflow-x-auto whitespace-nowrap">
              pip install "cerbia[cli]"
            </div>
          </div>
        </div>
        <div className="bg-background flex flex-col gap-3 justify-between items-start">
          <div className="flex flex-col gap-3 w-full">
            <div className="inline-flex size-7 text-[16px] leading-[20px] font-light items-center justify-center rounded-full bg-black text-white dark:bg-white dark:text-black">2</div>
            <h3 className="text-[20px] leading-[28px] font-light">Validate configuration</h3>
            <p className="text-[16px] leading-[22px] text-muted-foreground font-light md:min-h-[72px]">
              Check that your YAML gate definitions are valid.
            </p>
            <div className="w-full p-4 border border-border font-mono text-sm bg-muted/30 overflow-x-auto whitespace-nowrap">
              cerbia validate examples/cli-usage/config.cerbia.yaml
            </div>
          </div>
        </div>
        <div className="bg-background flex flex-col gap-3 justify-between items-start">
          <div className="w-full flex flex-col gap-3">
            <div className="inline-flex size-7 text-[16px] leading-[20px] font-light items-center justify-center rounded-full bg-black text-white dark:bg-white dark:text-black">3</div>
            <h3 className="text-[20px] leading-[28px] font-light">Scan content</h3>
            <p className="text-[16px] leading-[22px] text-muted-foreground font-light md:min-h-[72px]">
              Run the gate against inline text or files to get a security verdict.
            </p>
            <div className="w-full p-4 border border-border font-mono text-sm bg-muted/30 overflow-x-auto whitespace-nowrap">
              cerbia scan --config examples/cli-usage/config.cerbia.yaml --text "A short message"
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function OpenSource() {
  return (
    <div className="w-full mt-[128px] py-[48px] border-border border-t-[1px] border-b-[1px] flex justify-center items-center px-6">
      <div className="max-w-[800px] flex flex-col gap-[24px] justify-center items-center">
        <div className="text-center text-[48px] leading-[56px] font-light uppercase">
          Free & Open Source
        </div>
        <div className="text-center text-[20px] leading-[28px] font-light">
          CerbIA is licensed under Apache-2.0. We welcome contributions to add new scanners, preprocessors, and integrations.
        </div>
        <div className="text-center mt-4">
          <LinkButton href="https://github.com/inditextech/cerbia" style="main" external>
            View Repository
          </LinkButton>
        </div>
      </div>
    </div>
  );
}

function End() {
  return (
    <div className="w-full py-[128px] text-white bg-black dark:bg-white dark:text-black flex justify-center items-center px-6">
      <div className="max-w-[800px] flex flex-col gap-[24px]">
        <div className="text-center text-[48px] leading-[56px] font-light uppercase">
          Ready to secure your AI workflows?
        </div>
        <div className="text-center text-[20px] leading-[28px] font-light">
          Read the documentation to learn how to compose gates and configure scanners.
        </div>
        <div className="text-center flex gap-[12px] justify-center items-center mt-4">
          <LinkButton href="/docs" variant="outline" className="border-white text-white hover:bg-zinc-800 dark:border-black dark:text-black dark:hover:bg-zinc-200">
            Get started
          </LinkButton>
        </div>
      </div>
    </div>
  );
}

type LinkButtonProps = {
  className?: string;
  href: string;
  external?: boolean;
  variant?: "default" | "outline";
  style?: "default" | "main";
  children: React.ReactNode;
};

const LinkButton = ({
  className = "",
  href,
  external = false,
  variant = "default",
  style = "default",
  children,
}: LinkButtonProps) => {
  let baseClass = "inline-flex items-center justify-center font-light text-[13px] uppercase cursor-pointer px-[32px] h-[40px] transition-colors rounded-none";

  if (style === "default" && variant === "outline") {
    baseClass += " border border-border bg-transparent text-foreground hover:bg-muted";
  } else if (style === "main") {
    baseClass += " bg-black hover:bg-[#757575] border border-black text-white dark:bg-white dark:hover:bg-[#454545] dark:text-black dark:hover:text-white dark:border-white dark:hover:border-[#454545]";
  }

  const target = external ? "_blank" : undefined;
  const rel = external ? "noopener noreferrer" : undefined;

  return (
    <Link href={href} className={`${baseClass} ${className}`} target={target} rel={rel}>
      {children}
    </Link>
  );
};
