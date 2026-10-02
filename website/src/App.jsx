import { useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Features from './pages/Features';
import Download from './pages/Download';
import FAQ from './pages/FAQ';
import About from './pages/About';
import Contact from './pages/Contact';
import NotFound from './pages/NotFound';
import { Terms, Privacy, Cookies, AcceptableUse, Eula, Disclaimer } from './pages/legal';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ForgotPassword from './pages/auth/ForgotPassword';
import AccountLayout from './pages/account/AccountLayout';
import Dashboard from './pages/account/Dashboard';
import License from './pages/account/License';
import Updates from './pages/account/Updates';
import Profile from './pages/account/Profile';
import LoginLogs from './pages/account/LoginLogs';
import Renewals from './pages/account/Renewals';

const titles = {
  '/': 'EzyMailer — Campaigns at light speed',
  '/features': 'Features — EzyMailer',
  '/download': 'Download — EzyMailer',
  '/faq': 'FAQ — EzyMailer',
  '/about': 'About — EzyMailer',
  '/contact': 'Contact — EzyMailer',
  '/terms': 'Terms of Service — EzyMailer',
  '/privacy': 'Privacy Policy — EzyMailer',
  '/cookies': 'Cookie Policy — EzyMailer',
  '/acceptable-use': 'Acceptable Use Policy — EzyMailer',
  '/eula': 'EULA — EzyMailer',
  '/disclaimer': 'Disclaimer — EzyMailer',
  '/login': 'Sign in — EzyMailer',
  '/register': 'Create account — EzyMailer',
  '/forgot-password': 'Reset password — EzyMailer',
  '/account': 'Dashboard — EzyMailer',
  '/account/license': 'Licence — EzyMailer',
  '/account/updates': 'Updates & news — EzyMailer',
  '/account/profile': 'Profile & security — EzyMailer',
  '/account/logins': 'Login logs — EzyMailer',
  '/account/renewals': 'Renewal history — EzyMailer',
};

export default function App() {
  const { pathname } = useLocation();
  useEffect(() => {
    document.title = titles[pathname] ?? 'Page not found — EzyMailer';
  }, [pathname]);

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="features" element={<Features />} />
        <Route path="download" element={<Download />} />
        <Route path="faq" element={<FAQ />} />
        <Route path="about" element={<About />} />
        <Route path="contact" element={<Contact />} />
        <Route path="terms" element={<Terms />} />
        <Route path="privacy" element={<Privacy />} />
        <Route path="cookies" element={<Cookies />} />
        <Route path="acceptable-use" element={<AcceptableUse />} />
        <Route path="eula" element={<Eula />} />
        <Route path="disclaimer" element={<Disclaimer />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="forgot-password" element={<ForgotPassword />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="account" element={<AccountLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="license" element={<License />} />
        <Route path="updates" element={<Updates />} />
        <Route path="profile" element={<Profile />} />
        <Route path="logins" element={<LoginLogs />} />
        <Route path="renewals" element={<Renewals />} />
      </Route>
    </Routes>
  );
}
