import { cn } from '@extension/ui';

interface VersionSelectorProps {
  currentVersion: number;
  totalVersions: number;
  onVersionChange: (version: number) => void;
  isLight: boolean;
  branchName?: string;
}

export const VersionSelector: React.FC<VersionSelectorProps> = ({
  currentVersion,
  totalVersions,
  onVersionChange,
  isLight,
  branchName,
}) => {
  if (totalVersions <= 1) return null;

  const handlePrevious = () => {
    if (currentVersion > 1) {
      onVersionChange(currentVersion - 1);
    }
  };

  const handleNext = () => {
    if (currentVersion < totalVersions) {
      onVersionChange(currentVersion + 1);
    }
  };

  return (
    <div
      className={cn('flex items-center gap-2 rounded-md px-2 py-1 text-sm', isLight ? 'bg-gray-100' : 'bg-gray-800')}>
      {branchName && (
        <div className="mr-2 flex items-center gap-1">
          <svg
            className={cn('h-3.5 w-3.5', isLight ? 'text-gray-500' : 'text-gray-400')}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
          <span className={cn('text-xs', isLight ? 'text-gray-600' : 'text-gray-400')}>{branchName}</span>
        </div>
      )}

      <button
        onClick={handlePrevious}
        disabled={currentVersion <= 1}
        className={cn(
          'flex h-6 w-6 items-center justify-center rounded transition-all',
          currentVersion > 1
            ? isLight
              ? 'text-gray-600 hover:bg-gray-200'
              : 'text-gray-300 hover:bg-gray-700'
            : isLight
              ? 'cursor-not-allowed text-gray-300'
              : 'cursor-not-allowed text-gray-600',
        )}
        title="上一个版本">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <span className={cn('min-w-[3rem] text-center', isLight ? 'text-gray-700' : 'text-gray-300')}>
        {currentVersion} / {totalVersions}
      </span>

      <button
        onClick={handleNext}
        disabled={currentVersion >= totalVersions}
        className={cn(
          'flex h-6 w-6 items-center justify-center rounded transition-all',
          currentVersion < totalVersions
            ? isLight
              ? 'text-gray-600 hover:bg-gray-200'
              : 'text-gray-300 hover:bg-gray-700'
            : isLight
              ? 'cursor-not-allowed text-gray-300'
              : 'cursor-not-allowed text-gray-600',
        )}
        title="下一个版本">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
};
