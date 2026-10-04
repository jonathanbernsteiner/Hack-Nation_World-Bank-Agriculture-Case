function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;
}

export default function Loading() {
  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="bg-white border border-line rounded-xl p-6">
              <Skeleton className="w-10 h-10 !rounded-full mb-4" />
              <Skeleton className="w-20 h-7" />
              <Skeleton className="w-28 h-4 mt-2" />
              <Skeleton className="w-32 h-3 mt-2" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-6">
          <div className="bg-white border border-line rounded-xl h-[620px] p-4">
            <Skeleton className="w-full h-full" />
          </div>
          <div className="bg-white border border-line rounded-xl h-[620px] p-6 flex flex-col gap-4">
            <Skeleton className="w-40 h-6" />
            <Skeleton className="w-full h-24" />
            <Skeleton className="w-full h-40" />
          </div>
        </div>
    </div>
  );
}
