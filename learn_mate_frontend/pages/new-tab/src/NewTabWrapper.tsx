import { AuthProvider } from './contexts/AuthContext';
import NewTab from './NewTab';

const NewTabWrapper = () => (
  <AuthProvider>
    <NewTab />
  </AuthProvider>
);

export default NewTabWrapper;
