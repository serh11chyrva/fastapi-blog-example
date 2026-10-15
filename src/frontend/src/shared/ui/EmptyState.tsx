export function EmptyState({ title, body }: {
  title: string;
  body: string;
}) {
  return <div className="surface px-6 py-12 text-center">
    <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-50 text-xl text-slate-600">✦</div>
    <h2 className="mt-4 font-semibold text-slate-900">
      {title}
    </h2>
    <p className="mx-auto mt-1 max-w-sm text-sm leading-6 text-slate-500">
      {body}
    </p>
  </div>;
}
