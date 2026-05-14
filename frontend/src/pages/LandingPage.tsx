import { Link } from "react-router-dom";
import { ArrowRightIcon, ChartBarIcon, SparklesIcon } from "@heroicons/react/24/outline";
import { useScrollReveal } from "../hooks/useScrollReveal";
import { useAuthStore } from "../store/authStore";

export default function LandingPage() {
  return (
    <div className="bg-landing-bg text-landing-ink min-h-screen">
      <Hero />
      <HowItWorks />
      <ClosingCTA />
    </div>
  );
}

function Hero() {
  const user = useAuthStore((s) => s.user);

  return (
    <section className="relative overflow-hidden">
      {/* Background ornament: large faded "S" anchor on the right */}
      <div
        className="absolute right-[-5vw] top-1/2 -translate-y-1/2 pointer-events-none select-none landing-fade-in"
        style={{ animationDelay: "200ms" }}
        aria-hidden="true"
      >
        <span className="font-serif text-[36vw] leading-none text-landing-ink/[0.04] block">
          S
        </span>
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-24 pb-32 md:pt-32 md:pb-40">
        <h1
          className="font-serif text-5xl md:text-7xl lg:text-8xl font-medium text-landing-ink leading-[0.95] tracking-tight mb-8 max-w-5xl landing-fade-up landing-delay-100"
          style={{ textWrap: "balance" } as React.CSSProperties}
        >
          An online store that{" "}
          <span className="italic text-brand-500">learns from you</span> as you shop.
        </h1>

        <p
          className="text-lg md:text-xl text-landing-inkMuted max-w-2xl leading-relaxed mb-12 landing-fade-up landing-delay-200"
          style={{ textWrap: "balance" } as React.CSSProperties}
        >
          SmartCart is a working e-commerce demo built around a deep reinforcement
          learning agent, the kind of AI that lives in research papers, here applied
          to the everyday experience of shopping online.
        </p>

        <div className="flex flex-wrap items-center gap-3 landing-fade-up landing-delay-300">
          <Link
            to="/shop"
            className="group inline-flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white px-6 py-3 rounded-full font-medium transition-colors"
          >
            Browse the shop
            <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>

          {user ? (
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 border border-landing-subtle hover:border-landing-inkMuted text-landing-ink px-6 py-3 rounded-full font-medium transition-colors"
            >
              <ChartBarIcon className="w-4 h-4" />
              View the dashboard
            </Link>
          ) : (
            <Link
              to="/register"
              className="inline-flex items-center gap-2 border border-landing-subtle hover:border-landing-inkMuted text-landing-ink px-6 py-3 rounded-full font-medium transition-colors"
            >
              Create an account
            </Link>
          )}
        </div>

        <p
          className="mt-10 text-xs font-mono text-landing-inkSubtle landing-fade-up landing-delay-500"
        >
          ↓ How it works
        </p>
      </div>
    </section>
  );
}

function HowItWorks() {
  const { ref, isVisible } = useScrollReveal<HTMLElement>();

  return (
    <section ref={ref} className="border-t border-landing-subtle bg-landing-surface/30">
      <div className="max-w-6xl mx-auto px-6 py-24 md:py-32">
        <div className={isVisible ? "landing-fade-up" : "opacity-0"}>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-brand-500 mb-4">
            How it works
          </p>
          <h2 className="font-serif text-3xl md:text-5xl text-landing-ink leading-tight mb-6 max-w-3xl"
            style={{ textWrap: "balance" } as React.CSSProperties}>
            Most "AI recommendations" don't actually learn.{" "}
            <span className="italic text-brand-500">This one does.</span>
          </h2>
          <p className="text-lg text-landing-inkMuted max-w-2xl leading-relaxed">
            Every typical recommendation engine ships a model trained once on
            historical data, then serves it unchanged. SmartCart closes the loop,
            updating from your actual behaviour in real time.
          </p>
        </div>

        <div className="mt-20 grid md:grid-cols-3 gap-8 md:gap-6">
          <Step
            number="01"
            title="The agent observes"
            body="Every product you view, click, or add to your cart is captured as a state: what you've been looking at, in what order, with what attention."
            delay={isVisible ? "landing-delay-200" : ""}
            visible={isVisible}
          />
          <Step
            number="02"
            title="The agent acts"
            body="From that state, a Deep Q-Network produces ranked recommendations. The agent estimates which products are most likely to interest you, then shows them."
            delay={isVisible ? "landing-delay-400" : ""}
            visible={isVisible}
          />
          <Step
            number="03"
            title="The agent learns"
            body="When you add a recommended product to your cart, that's positive reward. The agent updates its policy. Next time you visit, the recommendations are different, better."
            delay={isVisible ? "landing-delay-700" : ""}
            visible={isVisible}
          />
        </div>

        <div className={`mt-20 ${isVisible ? "landing-fade-up landing-delay-900" : "opacity-0"}`}>
          <div className="bg-landing-bg border border-landing-subtle rounded-2xl p-8 md:p-12 max-w-4xl">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-10 h-10 rounded-full bg-brand-500/10 border border-brand-500/30 grid place-items-center shrink-0">
                <SparklesIcon className="w-5 h-5 text-brand-500" />
              </div>
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-brand-500 mb-2">
                  Why this matters
                </p>
                <h3 className="font-serif text-2xl md:text-3xl text-landing-ink leading-tight mb-4"
                  style={{ textWrap: "balance" } as React.CSSProperties}>
                  You can watch the agent improve during a single browsing session.
                </h3>
              </div>
            </div>
            <p className="text-landing-inkMuted leading-relaxed pl-14">
              The dashboard compares the agent against a collaborative-filtering
              baseline, the classical approach used by most e-commerce sites, and
              shows you which one is converting better, in real time. After a handful
              of interactions, you'll see the curves separate.
            </p>
            <div className="pl-14 mt-6">
              <Link
                to="/shop"
                className="inline-flex items-center gap-2 text-brand-500 hover:text-brand-400 text-sm font-medium group"
              >
                Try it for yourself
                <ArrowRightIcon className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Step({
  number,
  title,
  body,
  delay,
  visible,
}: {
  number: string;
  title: string;
  body: string;
  delay: string;
  visible: boolean;
}) {
  return (
    <div className={visible ? `landing-fade-up ${delay}` : "opacity-0"}>
      <div className="flex items-center gap-4 mb-4">
        <span className="font-mono text-xs text-brand-500 tracking-widest">{number}</span>
        <div className="flex-1 h-px bg-landing-subtle landing-strip-grow" style={{ animationDelay: delay ? "200ms" : "0ms" }} />
      </div>
      <h3 className="font-serif text-2xl text-landing-ink mb-3 leading-tight">{title}</h3>
      <p className="text-landing-inkMuted leading-relaxed text-[15px]">{body}</p>
    </div>
  );
}

function ClosingCTA() {
  const { ref, isVisible } = useScrollReveal<HTMLElement>();

  return (
    <section ref={ref} className="border-t border-landing-subtle">
      <div className="max-w-4xl mx-auto px-6 py-24 md:py-32 text-center">
        <div className={isVisible ? "landing-fade-up" : "opacity-0"}>
          <p className="text-xs font-mono uppercase tracking-[0.2em] text-brand-500 mb-6">
            Take a look
          </p>
          <h2 className="font-serif text-3xl md:text-5xl text-landing-ink mb-6 leading-tight"
            style={{ textWrap: "balance" } as React.CSSProperties}>
            The store is real. So is the AI.
          </h2>
          <p className="text-lg text-landing-inkMuted mb-10 max-w-xl mx-auto leading-relaxed">
            Browse products, add to cart, log in to see your personalised
            recommendations and the live policy comparison dashboard.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/shop"
              className="group inline-flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white px-6 py-3 rounded-full font-medium transition-colors"
            >
              Start shopping
              <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            
              <a
              href="https://github.com/IAdejokun"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 border border-landing-subtle hover:border-landing-inkMuted text-landing-ink px-6 py-3 rounded-full font-medium transition-colors"
            >
              View on GitHub
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}