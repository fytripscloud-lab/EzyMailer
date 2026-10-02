import LegalPage from '../../components/LegalPage';
import { legalDocs } from '../../data/legal';

export const Terms = () => <LegalPage doc={legalDocs.terms} />;
export const Privacy = () => <LegalPage doc={legalDocs.privacy} />;
export const Cookies = () => <LegalPage doc={legalDocs.cookies} />;
export const AcceptableUse = () => <LegalPage doc={legalDocs.acceptableUse} />;
export const Eula = () => <LegalPage doc={legalDocs.eula} />;
export const Disclaimer = () => <LegalPage doc={legalDocs.disclaimer} />;
