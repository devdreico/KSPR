import { useEffect, useState } from "react";

type TypewriterProps = {
  text: string;
  speed?: number;
  className?: string;
};

export function Typewriter({ text, speed = 20, className }: TypewriterProps) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const instant =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (instant) {
      setCount(text.length);
      return;
    }

    setCount(0);
    let index = 0;
    const id = window.setInterval(() => {
      index += 1;
      setCount(index);
      if (index >= text.length) window.clearInterval(id);
    }, speed);

    return () => window.clearInterval(id);
  }, [text, speed]);

  return (
    <span className={className}>
      {text.slice(0, count)}
      {count < text.length && <span className="caret" aria-hidden="true" />}
    </span>
  );
}
