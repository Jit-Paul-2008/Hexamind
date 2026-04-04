"use client";

type Props = {
  items: string[];
};

export default function ContradictionView({ items }: Props) {
  if (!items.length) {
    return <p className="text-sm text-white/55">No contradictions detected for this run.</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="rounded-md border border-amber-200/30 bg-amber-200/10 p-2 text-sm text-amber-50">
          {item}
        </li>
      ))}
    </ul>
  );
}
