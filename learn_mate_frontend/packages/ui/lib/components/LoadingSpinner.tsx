import { RingLoader } from 'react-spinners';

interface ILoadingSpinnerProps {
  size?: number;
  fullScreen?: boolean;
}

export const LoadingSpinner = ({ size, fullScreen = false }: ILoadingSpinnerProps) => (
  <div className={fullScreen ? 'flex min-h-screen items-center justify-center' : 'flex items-center justify-center'}>
    <RingLoader size={size ?? 100} color={'aqua'} />
  </div>
);
