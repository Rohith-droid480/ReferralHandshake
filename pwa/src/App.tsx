import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ModeBanner } from './components/ModeBanner';
import { DemoRoleSwitcher } from './components/DemoRoleSwitcher';
import { DemoScenariosBar } from './components/DemoScenariosBar';
import { ArenaBigScreen } from './views/ArenaBigScreen';
import { JudgeJoin } from './views/JudgeJoin';
import { JudgeDesk } from './views/JudgeDesk';
import { ClinicianCard } from './views/ClinicianCard';
import { ReceivingDesk } from './views/ReceivingDesk';
import { AmbulancePwa } from './views/AmbulancePwa';
import { DispatcherConsole } from './views/DispatcherConsole';
import { CommandCentre } from './views/CommandCentre';
import {
  Tv,
  QrCode,
  Award,
  Stethoscope,
  Hospital,
  Navigation,
  PhoneCall,
  Activity,
} from 'lucide-react';

const NavigationNav: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Guarantee Arena', icon: Tv },
    { path: '/judge-join', label: 'QR Join', icon: QrCode },
    { path: '/judge-desk', label: 'Judge Desk', icon: Award },
    { path: '/clinician', label: 'Clinician Card', icon: Stethoscope },
    { path: '/receiving-desk', label: 'Receiving Desk', icon: Hospital },
    { path: '/ambulance', label: 'Ambulance PWA', icon: Navigation },
    { path: '/dispatcher', label: 'Dispatcher Hub', icon: PhoneCall },
    { path: '/command-centre', label: 'Command Centre', icon: Activity },
  ];

  return (
    <nav className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center gap-1 overflow-x-auto text-xs">
      {navItems.map((item) => {
        const Icon = item.icon;
        const active = location.pathname === item.path;
        return (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition ${
              active
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <ModeBanner />
        <DemoRoleSwitcher />
        <DemoScenariosBar />
        <NavigationNav />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<ArenaBigScreen />} />
            <Route path="/arena" element={<ArenaBigScreen />} />
            <Route path="/judge-join" element={<JudgeJoin />} />
            <Route path="/judge-desk" element={<JudgeDesk />} />
            <Route path="/clinician" element={<ClinicianCard />} />
            <Route path="/receiving-desk" element={<ReceivingDesk />} />
            <Route path="/ambulance" element={<AmbulancePwa />} />
            <Route path="/dispatcher" element={<DispatcherConsole />} />
            <Route path="/command-centre" element={<CommandCentre />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;

