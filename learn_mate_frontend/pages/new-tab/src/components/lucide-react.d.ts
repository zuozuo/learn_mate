declare module 'lucide-react' {
  import type { FC, SVGProps } from 'react';

  export interface IconProps extends SVGProps<SVGSVGElement> {
    size?: string | number;
    absoluteStrokeWidth?: boolean;
  }

  export const Plus: FC<IconProps>;
  export const MessageSquare: FC<IconProps>;
  export const Trash2: FC<IconProps>;
  export const Search: FC<IconProps>;
}
