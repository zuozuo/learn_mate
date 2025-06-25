import '@src/index.css';
import NewTabWrapper from '@src/NewTabWrapper';
import { createRoot } from 'react-dom/client';

const init = () => {
  const appContainer = document.querySelector('#app-container');
  if (!appContainer) {
    throw new Error('Can not find #app-container');
  }
  const root = createRoot(appContainer);

  root.render(<NewTabWrapper />);
};

init();
