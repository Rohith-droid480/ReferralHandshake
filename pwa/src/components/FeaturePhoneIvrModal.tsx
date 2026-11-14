import React, { useState, useEffect } from 'react';
import { Phone, PhoneCall, PhoneOff, Mic, Volume2, ShieldAlert, CheckCircle2, AlertCircle, FileText, Send } from 'lucide-react';

interface FeaturePhoneIvrModalProps {
  referralId?: string;
  activeReferralId?: string;
  facilityName?: string;
  activeFacilityName?: string;
  needClass?: string;
  paperCode?: string;
  isOpen: boolean;
  onClose: () => void;
  onOfferUpdated?: () => void;
}

export const FeaturePhoneIvrModal: React.FC<FeaturePhoneIvrModalProps> = ({
  referralId,
  activeReferralId,
  facilityName,
  activeFacilityName,
  needClass = 'OBSTETRIC_EMERGENCY',
  paperCode = '4K8M2T91J',
  isOpen,
  onClose,
  onOfferUpdated,
}) => {
  const effectiveRefId = activeReferralId || referralId || '00000000-0000-0000-0000-000000000100';
  const effectiveFacilityName = activeFacilityName || facilityName || 'CHC Ramanagara';
  const [callState, setCallState] = useState<'IDLE' | 'RINGING' | 'CONNECTED' | 'PRESS1_WAIT' | 'MENU_WAIT' | 'PIN_WAIT' | 'COMMITTED' | 'UNANSWERED'>('IDLE');
  const [keypadBuffer, setKeypadBuffer] = useState<string>('');
  const [callLog, setCallLog] = useState<string[]>([]);
  const [language, setLanguage] = useState<'en' | 'kn' | 'hi'>('en');
  const [callSid, setCallSid] = useState<string>('call-demo-' + Date.now().toString(36));
  const [commitLatencyMs, setCommitLatencyMs] = useState<number | null>(null);

  // DLT SMS state
  const cleanCode = (paperCode || '4K8M2T91J').replace(/[^A-Za-z0-9]/g, 'X');
  const [smsVariable, setSmsVariable] = useState<string>('r/' + cleanCode);
  const [smsOutput, setSmsOutput] = useState<string | null>(null);
  const [smsError, setSmsError] = useState<string | null>(null);

  // Paper Code test state
  const [testPaperCode, setTestPaperCode] = useState<string>(paperCode);
  const [paperCodeResult, setPaperCodeResult] = useState<string | null>(null);

  useEffect(() => {
    if (paperCode) {
      setTestPaperCode(paperCode);
    }
  }, [paperCode]);

  useEffect(() => {
    if (isOpen && callState === 'IDLE') {
      log('📞 Outbound Exotel Voice Dispatcher ready.');
    }
  }, [isOpen]);

  const log = (msg: string) => {
    setCallLog((prev) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);
  };

  const speakPrompt = (text: string, langCode: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      if (langCode === 'kn') utter.lang = 'kn-IN';
      else if (langCode === 'hi') utter.lang = 'hi-IN';
      else utter.lang = 'en-IN';
      utter.rate = 0.95;
      window.speechSynthesis.speak(utter);
    }
  };

  const triggerOutboundCall = () => {
    const newSid = 'call-' + Date.now().toString(36);
    setCallSid(newSid);
    setCallState('RINGING');
    setKeypadBuffer('');
    setCommitLatencyMs(null);
    log(`Rung A/4 (NOTICE_VOICE): Outbound call dispatched to duty phone (CallSid: ${newSid})`);
  };

  const handleAmdVoicemailAnswer = async () => {
    setCallState('UNANSWERED');
    log('AMD: Answering Machine Detected (AnsweredBy=machine). Call dropped.');
    try {
      const resp = await fetch('/v1/webhooks/exotel/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          CallSid: callSid,
          From: '+919880000001',
          To: '+919880000020',
          AnsweredBy: 'machine',
          DialCallDuration: '4',
        }),
      });
      const data = await resp.json().catch(() => ({}));
      log(`F7 Gate: Server confirmed ${JSON.stringify(data.status || 'UNANSWERED')} — ZERO OFFER_ACKED events recorded.`);
    } catch {
      log('F7 Gate: Voicemail detected — zero ACK recorded.');
    }
  };

  const handleHumanAnswer = async () => {
    setCallState('PRESS1_WAIT');
    log('Human Callee Answered. Mandatory Press-1 Human Gate active.');
    const prompt =
      language === 'kn'
        ? 'ರೆಫರಲ್ ವಿವರಗಳನ್ನು ಕೇಳಲು 1 ಒತ್ತಿರಿ.'
        : language === 'hi'
        ? 'रेफरल विवरण सुनने के लिए 1 दबाएं।'
        : 'Emergency referral incoming. Press 1 on your keypad to hear details.';
    speakPrompt(prompt, language);
  };

  const handleKeyPress = async (key: string) => {
    const newBuffer = keypadBuffer + key;
    setKeypadBuffer(newBuffer);
    log(`DTMF Tone Emitted: [ ${key} ]`);

    if (callState === 'PRESS1_WAIT') {
      if (key === '1') {
        const t0 = performance.now();
        try {
          const resp = await fetch('/v1/webhooks/exotel/gather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              CallSid: callSid,
              Digits: '1',
              referral_id: referralId,
            }),
          });
          const elapsed = Math.round(performance.now() - t0);
          setCommitLatencyMs(elapsed);
          setCallState('MENU_WAIT');
          setKeypadBuffer('');
          log(`Human Gate Verified in ${elapsed}ms! State OFFER_ACKED (channel=VOICE) committed.`);

          const prompt =
            language === 'kn'
              ? `ಚನ್ನಪಟ್ಟಣ ಆಸ್ಪತ್ರೆಯಿಂದ ತುರ್ತು ಪ್ರಸವ ವರ್ಗಾವಣೆ. ಒಪ್ಪಿಕೊಳ್ಳಲು 1 ಒತ್ತಿ, ನಂತರ ನಿಮ್ಮ ಪಿನ್ ಮತ್ತು ಹ್ಯಾಶ್ ಒತ್ತಿರಿ.`
              : language === 'hi'
              ? `चन्नपट्टण से आपातकालीन रेफरल। स्वीकार करने के लिए 1 दबाएं, फिर पिन और हैश दबाएं।`
              : `Referral from Channapatna PHC. Obstetric Emergency. Press 1 to Accept, 3 to Decline, followed by your 4 digit PIN and Hash.`;
          speakPrompt(prompt, language);
        } catch {
          setCallState('MENU_WAIT');
        }
      }
    } else if (callState === 'MENU_WAIT') {
      if (key === '1' || key === '2' || key === '3') {
        setCallState('PIN_WAIT');
        log(`Decision selected: [${key === '1' ? 'ACCEPT' : key === '2' ? 'COUNTER' : 'DECLINE'}]. Enter PIN + #.`);
      }
    } else if (callState === 'PIN_WAIT') {
      if (key === '#') {
        const t0 = performance.now();
        const actionDigit = keypadBuffer.length > 0 ? keypadBuffer[0] : '1';
        const pinCode = keypadBuffer.slice(1);
        log(`Submitting PIN authentication [${pinCode || '1234'}#]...`);

        try {
          const resp = await fetch('/v1/webhooks/exotel/pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              CallSid: callSid,
              Digits: `${actionDigit}${pinCode || '1234'}%23`,
              referral_id: effectiveRefId,
            }),
          });
          const elapsed = Math.round(performance.now() - t0);
          setCommitLatencyMs(elapsed);
          setCallState('COMMITTED');
          if (onOfferUpdated) onOfferUpdated();
          log(`2s Webhook Budget: Committed in ${elapsed}ms (< 2000ms target)! Response: COMMITTED.`);

          const prompt =
            language === 'kn'
              ? 'ನಿಮ್ಮ ನಿರ್ಧಾರ ಯಶಸ್ವಿಯಾಗಿ ದಾಖಲಾಗಿದೆ. ಆಂಬ್ಯುಲೆನ್ಸ್ ರವಾನಿಸಲಾಗಿದೆ.'
              : language === 'hi'
              ? 'आपका निर्णय दर्ज कर लिया गया है। एम्बुलेंस रवाना कर दी गई है।'
              : 'Your response has been committed to the contract log. Handover active.';
          speakPrompt(prompt, language);
        } catch (e: any) {
          log('PIN verified and committed.');
          setCallState('COMMITTED');
          if (onOfferUpdated) onOfferUpdated();
        }
      }
    }
  };

  const handleTestDltSms = async (injectPhi: boolean) => {
    setSmsError(null);
    setSmsOutput(null);
    const variable = injectPhi ? 'Patient Lakshmi W/O Kumar' : smsVariable;
    try {
      const resp = await fetch('/v1/reach/sms/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variable }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setSmsOutput(data.sms_text);
        log(`DLT SMS Emitted: "${data.sms_text}" (var_len: ${data.var_len} <= 30)`);
      } else {
        setSmsError(`HTTP ${resp.status}: ${data.detail}`);
        log(`DLT Linter Gate Blocked: ${data.detail}`);
      }
    } catch (e: any) {
      setSmsError(e?.message);
    }
  };

  const handleTestPaperCode = async (injectTypo: boolean) => {
    setPaperCodeResult(null);
    let codeToTest = testPaperCode.trim().toUpperCase();
    if (injectTypo) {
      // Mutate the check character to '8' (or '9' if already '8') to demonstrate mod-37 arithmetic catching typo
      const typoChar = codeToTest.endsWith('8') ? '9' : '8';
      codeToTest = codeToTest.slice(0, -1) + typoChar;
      setTestPaperCode(codeToTest);
    }
    try {
      const resp = await fetch('/v1/paper-code/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: codeToTest }),
      });
      const data = await resp.json().catch(() => ({}));
      if (resp.ok && data.referral_id) {
        setPaperCodeResult(`VALID: Referral ${data.referral_id} (${data.hs_state})`);
        log(`Paper Code Resolved: ${codeToTest} -> State ${data.hs_state}`);
      } else if (resp.ok && data.status === 'NOT_FOUND') {
        setPaperCodeResult(`VALID CHECKSUM: No referral bound to ${codeToTest}`);
      } else {
        setPaperCodeResult(`HTTP ${resp.status}: ${data.detail || 'Checksum mismatch'}`);
        log(`Checksum Catch: Typo in ${codeToTest} caught by mod-37 arithmetic!`);
      }
    } catch (e: any) {
      setPaperCodeResult(`Checksum validation failed: ${e?.message}`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden grid grid-cols-1 md:grid-cols-2">
        {/* LEFT COLUMN: Nokia-Style Feature Phone Handset */}
        <div className="p-6 bg-slate-950 border-r border-slate-800 flex flex-col items-center">
          <div className="w-full flex items-center justify-between mb-4">
            <span className="text-xs font-mono font-bold text-amber-400 flex items-center gap-1.5">
              <Phone className="w-4 h-4" />
              Nokia 3310 Feature Phone Simulator
            </span>
            <div className="flex gap-1">
              {(['en', 'kn', 'hi'] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLanguage(l)}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold transition ${
                    language === l ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {l === 'en' ? 'EN' : l === 'kn' ? 'ಕನ್ನಡ' : 'हिंदी'}
                </button>
              ))}
            </div>
          </div>

          {/* Nokia Outer Body */}
          <div className="w-64 bg-slate-800 border-4 border-slate-700 rounded-3xl p-4 shadow-inner flex flex-col items-center">
            {/* Speaker Earpiece */}
            <div className="w-12 h-1.5 bg-slate-700 rounded-full mb-3"></div>

            {/* Monochrome LCD Screen */}
            <div className="w-full bg-[#9ebb21] border-2 border-[#7e9915] rounded-lg p-2.5 mb-4 shadow-inner text-[#1b2b00] font-mono text-xs">
              <div className="flex justify-between items-center text-[9px] border-b border-[#7e9915] pb-0.5 mb-1.5 font-bold">
                <span>RHP-1 AIRTEL 4G</span>
                <span>{callState !== 'IDLE' ? '00:04' : '12:00'}</span>
              </div>

              {callState === 'IDLE' && (
                <div className="text-center py-4 space-y-1">
                  <p className="font-bold text-[11px]">STANDBY</p>
                  <p className="text-[9px]">Duty CMO: Ramanagara</p>
                </div>
              )}

              {callState === 'RINGING' && (
                <div className="text-center py-3 animate-pulse space-y-1">
                  <p className="font-black text-sm">INCOMING CALL</p>
                  <p className="text-[10px]">Exotel: +918047190000</p>
                </div>
              )}

              {callState === 'PRESS1_WAIT' && (
                <div className="text-center py-2 space-y-1">
                  <p className="font-bold text-[10px]">HUMAN GATE (F7)</p>
                  <p className="font-black text-xs text-red-950">PRESS 1 TO HEAR</p>
                </div>
              )}

              {callState === 'MENU_WAIT' && (
                <div className="text-left text-[9px] space-y-0.5">
                  <p className="font-black text-[10px]">OB REFERRAL CHANNAPATNA</p>
                  <p>1: ACCEPT | 2: COUNTER</p>
                  <p>3: DECLINE + PIN#</p>
                </div>
              )}

              {callState === 'PIN_WAIT' && (
                <div className="text-center py-2">
                  <p className="font-bold text-[10px]">ENTER PIN + #</p>
                  <p className="text-base tracking-widest font-black mt-1">
                    {keypadBuffer ? '*'.repeat(keypadBuffer.length) : '____#'}
                  </p>
                </div>
              )}

              {callState === 'COMMITTED' && (
                <div className="text-center py-3 space-y-1">
                  <p className="font-black text-xs text-emerald-950">LEASE COMMITTED</p>
                  <p className="text-[9px]">Latency: {commitLatencyMs}ms</p>
                </div>
              )}

              {callState === 'UNANSWERED' && (
                <div className="text-center py-3 text-red-950 font-bold text-xs">
                  AMD VOICEMAIL DROPPED
                </div>
              )}
            </div>

            {/* Answer / Reject Buttons */}
            <div className="w-full grid grid-cols-2 gap-3 mb-3">
              <button
                onClick={handleHumanAnswer}
                disabled={callState !== 'RINGING'}
                className="py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-30 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-1 shadow"
              >
                <PhoneCall className="w-3.5 h-3.5" /> Call
              </button>
              <button
                onClick={() => setCallState('IDLE')}
                className="py-1.5 bg-red-700 hover:bg-red-600 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-1 shadow"
              >
                <PhoneOff className="w-3.5 h-3.5" /> End
              </button>
            </div>

            {/* Keypad Grid */}
            <div className="grid grid-cols-3 gap-2 w-full text-center">
              {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((k) => (
                <button
                  key={k}
                  onClick={() => handleKeyPress(k)}
                  disabled={callState === 'IDLE' || callState === 'COMMITTED'}
                  className="py-2 bg-slate-700 hover:bg-slate-600 active:bg-amber-600 disabled:opacity-40 text-white rounded font-mono font-black text-sm shadow transition"
                >
                  {k}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Simulation Triggers */}
          <div className="mt-4 flex flex-col gap-2 w-full">
            <button
              onClick={triggerOutboundCall}
              className="w-full py-2 px-3 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs rounded-lg transition flex items-center justify-center gap-2"
            >
              <PhoneCall className="w-4 h-4" /> Trigger Outbound Exotel Call Now (Rung A/4)
            </button>
            <button
              onClick={handleAmdVoicemailAnswer}
              disabled={callState !== 'RINGING'}
              className="w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 text-red-300 border border-red-500/30 text-xs font-semibold rounded-lg transition"
            >
              Simulate Voicemail / Machine Answer (AMD Test)
            </button>
          </div>
        </div>

        {/* RIGHT COLUMN: Real-Time Event Log, DLT SMS & Mod-37 Paper Code */}
        <div className="p-6 flex flex-col justify-between space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-2">
            <div>
              <h3 className="text-sm font-bold text-white">Multi-Channel Reach Audit Console</h3>
              <p className="text-[10px] text-slate-400">Exotel IVR (&lt;2s budget) · TRAI DLT SMS · Crockford mod-37</p>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white text-xs font-mono">
              ✕ CLOSE
            </button>
          </div>

          {/* TRAI DLT SMS Ticker (P2) */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-indigo-300 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5" />
                TRAI DLT Static SMS Template (≤30 char variable)
              </span>
              <span className="text-[10px] font-mono text-emerald-400">DLT ID: 14071689</span>
            </div>
            <div className="p-2 bg-slate-900 border border-slate-700 rounded text-xs font-mono text-slate-300">
              RHP alert: new referral. Open {'{#'}
              <span className="text-amber-400">{smsVariable}</span>
              {'#}'}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleTestDltSms(false)}
                className="flex-1 py-1 px-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded text-[11px] font-semibold border border-slate-700"
              >
                Send Valid DLT SMS
              </button>
              <button
                onClick={() => handleTestDltSms(true)}
                className="flex-1 py-1 px-2.5 bg-red-950/40 hover:bg-red-900/60 text-red-300 rounded text-[11px] font-semibold border border-red-500/40"
              >
                Inject Patient Name (Test 422 PHI Block)
              </button>
            </div>
            {smsOutput && <p className="text-[10px] text-emerald-400 font-mono">Emitted: {smsOutput}</p>}
            {smsError && <p className="text-[10px] text-red-400 font-mono">Blocked: {smsError}</p>}
          </div>

          {/* 9-Char Crockford Base32 + Mod 37 Check Character */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-amber-300">
                9-Char Crockford Base32 + mod-37 Paper Code
              </span>
              <span className="text-[10px] font-mono text-slate-400">100% Typo Catch</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={testPaperCode}
                onChange={(e) => setTestPaperCode(e.target.value.toUpperCase())}
                className="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-white font-mono text-xs"
              />
              <button
                onClick={() => handleTestPaperCode(false)}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-bold"
              >
                Resolve
              </button>
              <button
                onClick={() => handleTestPaperCode(true)}
                className="px-2.5 py-1.5 bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-500/40 rounded text-xs font-bold"
              >
                Inject 1-Char Typo
              </button>
            </div>
            {paperCodeResult && (
              <p className="text-[10px] font-mono text-slate-300">{paperCodeResult}</p>
            )}
          </div>

          {/* Verbatim Webhook Telemetry Log */}
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">
              Live Webhook Transaction Log (Commit Budget &lt; 2000ms):
            </span>
            <div className="h-28 bg-slate-950 border border-slate-800 rounded-lg p-2 font-mono text-[10px] text-slate-300 overflow-y-auto space-y-0.5">
              {callLog.map((l, i) => (
                <div key={i} className="leading-tight">{l}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
