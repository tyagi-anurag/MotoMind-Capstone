// page.tsx
"use client";
import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Camera, Send, Activity, X, MapPin, Wrench, Map, AlertTriangle, User, Bike, ArrowRight, Navigation, Fuel, Menu } from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

type Message = {
  role: "user" | "agent";
  content: string;
  attachmentUrl?: string;
  attachmentType?: "audio" | "vision";
};

export default function MotoMindUI() {
  // <<-- SET THIS to your deployed backend URL (Render/Cloud Run) before committing
  const BACKEND_URL = "https://motomind-backend.onrender.com";
  // ------------------------------------------------------------------------------

  const [activeTab, setActiveTab] = useState("chat");
  const [messages, setMessages] = useState<Message[]>([
    { role: "agent", content: "I am MotoMind. I can see, hear, and plan your ride. \n\n**How can I help?**" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [showOnboarding, setShowOnboarding] = useState(true);
  const [userName, setUserName] = useState("");
  const [bikeModel, setBikeModel] = useState("");
  const [userLocation, setUserLocation] = useState("");
  const [isLocating, setIsLocating] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState<"audio" | "vision" | null>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const [mechanicsResult, setMechanicsResult] = useState("");
  const [tripResult, setTripResult] = useState<string | null>(null);
  const [tripMapLink, setTripMapLink] = useState("");

  // ---------------------
  // Utilities - image extraction & checks
  // ---------------------
  function extractImageUrlsFromText(text: string): string[] {
    if (!text) return [];
    const urls: string[] = [];

    // Markdown links [text](url)
    const mdLinkRe = /\[.*?\]\((https?:\/\/[^\s)]+)\)/gi;
    let mdMatch;
    while ((mdMatch = mdLinkRe.exec(text)) !== null) {
      const url = mdMatch[1];
      if (isDirectImageUrl(url)) urls.push(url);
    }

    // Plain urls ending with common image extensions
    const plainImgRe = /(https?:\/\/[^\s)]+?\.(?:png|jpe?g|gif|webp|bmp|svg)(?:\?[^\s)]*)?)/gi;
    let pMatch;
    while ((pMatch = plainImgRe.exec(text)) !== null) {
      urls.push(pMatch[1]);
    }

    return Array.from(new Set(urls));
  }

  function isDirectImageUrl(url: string) {
    if (!url) return false;
    try {
      const u = new URL(url);
      // Allow googleusercontent (direct image hosting), but skip normal google search pages
      if (u.hostname.includes("google.") && !u.hostname.includes("googleusercontent")) return false;
      if (u.hostname.includes("bing.") || u.hostname.includes("twitter.com")) return false;
      return /\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$/i.test(u.pathname + (u.search || ""));
    } catch (e) {
      return false;
    }
  }

  // ---------------------
  // Onboarding & location helpers
  // ---------------------
  const handleAutoLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const geoRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
          const geoData = await geoRes.json();
          const locationName = geoData.address?.city || geoData.address?.town || geoData.address?.village || `${latitude}, ${longitude}`;
          setUserLocation(locationName);
        } catch {
          setUserLocation(`${latitude}, ${longitude}`);
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        console.error(err);
        alert("Unable to retrieve location. Please allow location access.");
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  };

  const finishOnboarding = () => {
    if (!bikeModel || !userLocation) return;
    setShowOnboarding(false);
    setMessages([
      { role: "agent", content: `Welcome **${userName || "Rider"}**! Ready to ride with your **${bikeModel}** in \`${userLocation}\`. \n\n**How can I help you today?**` },
    ]);
  };

  // ---------------------
  // File selection handlers
  // ---------------------
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, type: "audio" | "vision") => {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
      setFileType(type);
      setActiveTab(type === "audio" ? "audio" : "vision");
    }
  };

  const clearAttachment = () => {
    setAttachedFile(null);
    setFileType(null);
    if (audioInputRef.current) audioInputRef.current.value = "";
    if (imageInputRef.current) imageInputRef.current.value = "";
  };

  // ---------------------
  // sendMessage: handles text, audio and vision uploads,
  // extracts direct image URLs from backend response text or images array,
  // attaches the first direct image to the agent bubble so the image displays inline.
  // ---------------------
  const sendMessage = async () => {
    if (!input && !attachedFile) return;

    const attachmentUrl = attachedFile ? URL.createObjectURL(attachedFile) : undefined;
    const attachmentType = fileType || undefined;

    const userMsg: Message = {
      role: "user",
      content: input || (attachedFile ? `[Uploaded ${fileType}]` : "..."),
      attachmentUrl,
      attachmentType,
    };

    setMessages((p) => [...p, userMsg]);
    setLoading(true);

    const currentInput = input;
    const currentFile = attachedFile;
    const currentType = fileType;

    setInput("");
    clearAttachment();

    try {
      let responseText = "";
      let responseImages: string[] = [];

      if (currentFile && currentType) {
        const formData = new FormData();
        formData.append("file", currentFile);
        formData.append("message", currentInput ? `Context: User has a ${bikeModel}. Question: ${currentInput}` : `Analyze this for a ${bikeModel}.`);
        const endpoint = currentType === "audio" ? "diagnose/audio" : "diagnose/vision";
        const res = await axios.post(`${BACKEND_URL}/${endpoint}`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        responseText = res.data?.response || "";
        responseImages = Array.isArray(res.data?.images) ? res.data.images : [];
      } else {
        const contextPrompt = `[Context: User: ${userName} | Location: ${userLocation} | Bike: ${bikeModel}] ${currentInput}`;
        const res = await axios.post(`${BACKEND_URL}/chat`, { message: contextPrompt });
        responseText = res.data?.response || "";
        responseImages = Array.isArray(res.data?.images) ? res.data.images : [];
      }

      // Prefer backend-provided images (only direct image urls)
      const validBackendImages = (responseImages || []).filter((u) => isDirectImageUrl(u));

      // Also attempt to extract direct image urls from response text
      const foundInText = extractImageUrlsFromText(responseText);

      const firstImage = validBackendImages.length > 0 ? validBackendImages[0] : (foundInText.length > 0 ? foundInText[0] : null);

      if (firstImage) {
        setMessages((prev) => [...prev, { role: "agent", content: responseText || "Here is what I found.", attachmentUrl: firstImage, attachmentType: "vision" }]);
      } else {
        setMessages((prev) => [...prev, { role: "agent", content: responseText || "I couldn't find any images." }]);
      }
    } catch (err) {
      console.error("sendMessage error:", err);
      setMessages((p) => [...p, { role: "agent", content: "⚠️ System Error: Could not reach MotoMind Brain." }]);
    } finally {
      setLoading(false);
    }
  };

  const findLocalMechanics = async () => {
    setLoading(true);
    setMechanicsResult("");
    try {
      const payload = `User Location: ${userLocation} | Bike: ${bikeModel}`;
      const res = await axios.post(`${BACKEND_URL}/find_mechanics`, { message: payload });
      setMechanicsResult(res.data?.response || "");
    } catch (e) {
      setMechanicsResult("Could not search for mechanics at this time.");
    } finally {
      setLoading(false);
    }
  };

  // ---------------------
  // JSX - preserved UI with the corrected message logic
  // ---------------------
  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white font-sans overflow-hidden relative flex flex-col md:flex-row">
      <AnimatePresence>
        {showOnboarding && (
          <motion.div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="bg-[#121212] border border-white/10 rounded-3xl p-6 md:p-8 max-w-md w-full shadow-2xl relative overflow-hidden" initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }}>
              <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-cyan-500 to-purple-500" />
              <div className="text-center mb-8">
                <div className="w-16 h-16 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-cyan-500/20 mx-auto mb-4">
                  <span className="text-3xl">🏍️</span>
                </div>
                <h2 className="text-2xl font-bold text-white">Setup MotoMind</h2>
                <p className="text-gray-400 text-sm mt-2">Configure your personal mechanic assistant.</p>
              </div>

              <div className="space-y-5">
                <div>
                  <label className="text-xs text-gray-500 uppercase font-bold tracking-wider ml-1">Your Name</label>
                  <div className="relative mt-2">
                    <User className="absolute left-3 top-3 text-gray-500" size={18} />
                    <input placeholder="e.g. Anurag" value={userName} onChange={(e) => setUserName(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl p-3 pl-10 text-white focus:border-cyan-500 outline-none transition-colors" />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase font-bold tracking-wider ml-1">Bike Model</label>
                  <div className="relative mt-2">
                    <Bike className="absolute left-3 top-3 text-gray-500" size={18} />
                    <input placeholder="e.g. Royal Enfield Classic 350" value={bikeModel} onChange={(e) => setBikeModel(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl p-3 pl-10 text-white focus:border-cyan-500 outline-none transition-colors" />
                  </div>
                </div>

                <div className="pt-2">
                  <label className="text-xs text-gray-500 uppercase font-bold tracking-wider ml-1">Current Location</label>
                  <div className="mt-3 space-y-3">
                    <button onClick={handleAutoLocation} disabled={isLocating} className="w-full py-3 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-xl border border-cyan-500/50 flex items-center justify-center gap-2 transition-all text-sm font-bold shadow-lg shadow-cyan-900/20">
                      {isLocating ? <Activity className="animate-spin" size={18} /> : <Navigation size={18} />}
                      {isLocating ? "Locating..." : "Detect Location Automatically"}
                    </button>

                    <div className="relative">
                      <MapPin className="absolute left-3 top-3 text-gray-500" size={18} />
                      <input value={userLocation} onChange={(e) => setUserLocation(e.target.value)} placeholder="Or type city manually..." className="w-full bg-white/5 border border-white/10 rounded-xl p-3 pl-10 text-white focus:border-cyan-500 outline-none transition-colors placeholder:text-gray-600" />
                    </div>
                  </div>
                </div>

                <button onClick={finishOnboarding} disabled={!bikeModel || !userLocation} className={`w-full py-4 mt-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all ${(!bikeModel || !userLocation) ? "bg-white/5 text-gray-600 cursor-not-allowed" : "bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-900/50"}`}>
                  Start Engine <ArrowRight size={20} />
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-purple-900/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-cyan-900/20 rounded-full blur-[120px]" />
      </div>

      {/* Sidebar (copy kept minimal but functionally same) */}
      <aside className={`fixed md:relative inset-y-0 left-0 z-40 w-80 bg-[#0a0a0a] md:bg-black/40 backdrop-blur-xl border-r border-white/10 p-6 flex flex-col gap-6 transition-transform duration-300 ease-in-out ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <span className="text-xl">🏍️</span>
            </div>
            <h1 className="font-bold text-xl tracking-wide">MotoMind <span className="text-cyan-400 font-light">Pro</span></h1>
          </div>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-gray-400 hover:text-white">
            <X size={24} />
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-white/5 p-4 rounded-xl border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <User size={14} className="text-gray-400" />
              <span className="text-xs text-gray-400 uppercase tracking-wider font-bold">Rider</span>
            </div>
            <div className="text-white font-medium">{userName || "Guest"}</div>
          </div>

          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Active Bike</label>
            <input value={bikeModel} onChange={(e) => setBikeModel(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-sm mt-1 focus:border-cyan-500 outline-none transition-colors" />
          </div>

          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Location</label>
            <div className="mt-2 space-y-2">
              <button onClick={handleAutoLocation} disabled={isLocating} className="w-full py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-lg border border-cyan-500/50 flex items-center justify-center gap-2 transition-all text-sm font-bold">
                {isLocating ? <Activity className="animate-spin" size={16} /> : <Navigation size={16} />}
                {isLocating ? "Locating..." : "Detect Location"}
              </button>
              <div className="relative">
                <MapPin className="absolute left-3 top-2.5 text-gray-500" size={16} />
                <input value={userLocation} onChange={(e) => setUserLocation(e.target.value)} placeholder="Or enter manually..." className="w-full bg-white/5 border border-white/10 rounded-lg p-2 pl-9 text-sm focus:border-cyan-500 outline-none transition-colors placeholder:text-gray-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-auto pt-6 border-t border-white/10">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Activity size={12} className="text-green-500" />
            <span>Systems Operational</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col relative z-10 h-screen w-full">
        <header className="px-4 md:px-6 py-4 border-b border-white/5 flex items-center gap-4 md:gap-6 bg-black/20 backdrop-blur-sm overflow-x-auto scrollbar-hide">
          <button onClick={() => setIsSidebarOpen(true)} className="md:hidden p-2 text-gray-400 hover:text-white transition-colors">
            <Menu size={24} />
          </button>
          {[{ id: "chat", label: "Chat", icon: Send }, { id: "vision", label: "Vision", icon: Camera }, { id: "audio", label: "Audio", icon: Mic }, { id: "travel", label: "Trip Planner", icon: Map }, { id: "rescue", label: "Rescue Map", icon: Wrench }].map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 text-sm font-medium pb-1 transition-all whitespace-nowrap ${activeTab === tab.id ? "text-cyan-400 border-cyan-400" : "text-gray-400 border-transparent hover:text-white hover:border-white/20"}`}>
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </header>

        <div className="flex-1 overflow-hidden flex flex-col">
          {(activeTab === "chat" || activeTab === "vision" || activeTab === "audio") && (
            <>
              <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10 pt-8 md:pt-12">
                {messages.map((msg, i) => (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[90%] md:max-w-[85%] p-4 rounded-2xl border backdrop-blur-sm shadow-xl ${msg.role === "user" ? "bg-cyan-900/30 border-cyan-500/30 rounded-tr-sm text-cyan-50" : "bg-white/5 border-white/10 rounded-tl-sm text-gray-200"}`}>
                      {msg.attachmentUrl && msg.attachmentType === "vision" && <img src={msg.attachmentUrl} alt="Upload" className="rounded-lg max-h-64 mb-3 border border-white/10" />}
                      {msg.attachmentUrl && msg.attachmentType === "audio" && <audio controls src={msg.attachmentUrl} className="w-full mb-3" />}
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown components={{ a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline" /> }}>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  </motion.div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-white/5 px-4 py-3 rounded-full flex gap-2 items-center border border-white/10">
                      <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce"></div>
                      <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce delay-75"></div>
                      <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce delay-150"></div>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 md:p-6 pt-0">
                <AnimatePresence>
                  {attachedFile && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} className="mb-3 flex items-center gap-3 bg-white/10 w-fit px-4 py-2 rounded-full border border-white/10">
                      {fileType === "audio" ? <Mic size={16} className="text-pink-400" /> : <Camera size={16} className="text-purple-400" />}
                      <span className="text-sm text-gray-200">{attachedFile.name}</span>
                      <button onClick={clearAttachment} className="hover:text-red-400 transition-colors">
                        <X size={16} />
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="bg-white/5 rounded-2xl border border-white/10 p-2 flex items-end gap-2 shadow-2xl backdrop-blur-md">
                  <div className="flex gap-1 pb-1 pl-1">
                    <input type="file" ref={audioInputRef} className="hidden" accept="audio/*" onChange={(e) => handleFileSelect(e, "audio")} />
                    <input type="file" ref={imageInputRef} className="hidden" accept="image/*" onChange={(e) => handleFileSelect(e, "vision")} />

                    <button onClick={() => audioInputRef.current?.click()} className={`p-3 rounded-xl transition-colors flex items-center gap-2 ${activeTab === "audio" ? "bg-pink-500/20 text-pink-400" : "hover:bg-white/10 text-gray-400"}`} title="Attach Audio">
                      <Mic size={20} />
                      <span className="text-xs font-bold hidden sm:inline">AUDIO</span>
                    </button>

                    <button onClick={() => imageInputRef.current?.click()} className={`p-3 rounded-xl transition-colors flex items-center gap-2 ${activeTab === "vision" ? "bg-purple-500/20 text-purple-400" : "hover:bg-white/10 text-gray-400"}`} title="Attach Image">
                      <Camera size={20} />
                      <span className="text-xs font-bold hidden sm:inline">PHOTO</span>
                    </button>
                  </div>

                  <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }} placeholder={activeTab === "audio" ? "Describe the sound..." : activeTab === "vision" ? "What should I look for?" : "Ask MotoMind..."} className="flex-1 bg-transparent border-none outline-none text-white px-2 py-3 max-h-32 min-h-[50px] resize-none placeholder:text-gray-600 text-lg" rows={1} />

                  <button onClick={sendMessage} disabled={!input && !attachedFile} className={`p-3 rounded-xl transition-all shadow-lg mb-1 ${input || attachedFile ? "bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-500/20" : "bg-white/5 text-gray-600 cursor-not-allowed"}`}>
                    <Send size={20} />
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Travel tab */}
          {activeTab === "travel" && (
            <div className="p-6 md:p-8 overflow-y-auto">
              <div className="max-w-2xl mx-auto space-y-6 pb-24">
                <div className="text-center mb-8">
                  <h2 className="text-2xl md:text-3xl font-bold text-white">Plan Your Ride</h2>
                  <p className="text-gray-400 text-sm md:text-base">Get a pro itinerary, bike prep advice, and route map.</p>
                </div>
                {!tripResult ? (
                  <div className="bg-white/5 p-6 rounded-2xl border border-white/10 space-y-6 shadow-2xl">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs text-gray-500 uppercase font-bold">From</label>
                        <input id="trip-from" placeholder="e.g. Delhi" className="w-full bg-black/20 border border-white/10 rounded-lg p-3 text-white focus:border-cyan-500 outline-none" />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase font-bold">To</label>
                        <input id="trip-to" placeholder="e.g. Ladakh" className="w-full bg-black/20 border border-white/10 rounded-lg p-3 text-white focus:border-cyan-500 outline-none" />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="md:col-span-2">
                        <label className="text-xs text-gray-500 uppercase font-bold">Bike</label>
                        <input id="trip-bike" defaultValue={bikeModel} className="w-full bg-black/20 border border-white/10 rounded-lg p-3 text-white focus:border-cyan-500 outline-none" />
                      </div>
                      <div className="grid grid-cols-2 gap-4 md:contents">
                        <div>
                          <label className="text-xs text-gray-500 uppercase font-bold">Days</label>
                          <input id="trip-days" type="number" placeholder="10" className="w-full bg-black/20 border border-white/10 rounded-lg p-3 text-white focus:border-cyan-500 outline-none" />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 uppercase font-bold">Riders</label>
                          <input id="trip-people" type="number" defaultValue="1" className="w-full bg-black/20 border border-white/10 rounded-lg p-3 text-white focus:border-cyan-500 outline-none" />
                        </div>
                      </div>
                    </div>

                    <button onClick={async () => {
                      setLoading(true);
                      const s = (document.getElementById("trip-from") as HTMLInputElement).value;
                      const d = (document.getElementById("trip-to") as HTMLInputElement).value;
                      const b = (document.getElementById("trip-bike") as HTMLInputElement).value;
                      const days = (document.getElementById("trip-days") as HTMLInputElement).value;
                      const p = (document.getElementById("trip-people") as HTMLInputElement).value || "1";
                      try {
                        const payload = `${s}|${d}|${b}|${days}|${p}`;
                        const res = await axios.post(`${BACKEND_URL}/plan_trip`, { message: payload });
                        const mapMatch = res.data.response.match(/(http.*?maps.*?)/);
                        if (mapMatch) setTripMapLink(mapMatch[1]);
                        setTripResult(res.data.response);
                      } catch {
                        alert("Trip planning failed.");
                      } finally {
                        setLoading(false);
                      }
                    }} className="w-full py-4 bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-bold rounded-xl shadow-lg hover:scale-[1.02] transition-transform flex items-center justify-center gap-2">
                      {loading ? <Activity className="animate-spin" /> : <Map size={20} />} GENERATE ITINERARY
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex flex-col md:flex-row gap-3">
                      <button onClick={() => setTripResult(null)} className="px-4 py-3 md:py-2 bg-white/10 rounded-lg text-sm hover:bg-white/20 transition-colors">← New Trip</button>
                      {tripMapLink && <a href={tripMapLink} target="_blank" rel="noopener noreferrer" className="flex-1 py-3 md:py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-colors"><MapPin size={16} /> OPEN ROUTE MAP</a>}
                      <button onClick={() => { setActiveTab("rescue"); findLocalMechanics(); }} className="flex-1 py-3 md:py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 transition-colors"><Fuel size={16} /> FIND MECHANICS</button>
                    </div>

                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6 md:p-8 shadow-2xl">
                      <div className="prose prose-invert max-w-none prose-headings:text-cyan-400 prose-h1:text-2xl md:prose-h1:text-3xl prose-h1:font-extrabold prose-h2:text-lg md:prose-h2:text-xl prose-h2:mt-6 prose-h2:border-b prose-h2:border-white/10 prose-h2:pb-2 prose-p:text-gray-300 prose-li:text-gray-300 prose-strong:text-white">
                        <ReactMarkdown>{tripResult || ""}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "rescue" && (
            <div className="p-6 md:p-8 overflow-y-auto">
              <div className="max-w-xl w-full mx-auto space-y-8 text-center pb-24">
                <div className="space-y-2 mt-4 md:mt-8">
                  <div className="w-16 h-16 md:w-20 md:h-20 bg-red-500/20 text-red-500 rounded-full flex items-center justify-center mx-auto animate-pulse">
                    <AlertTriangle size={32} className="md:w-10 md:h-10" />
                  </div>
                  <h2 className="text-2xl md:text-3xl font-bold text-white">Roadside Assistance</h2>
                  <p className="text-gray-400 text-sm md:text-base">Find local mechanics near <span className="text-white font-bold">{userLocation || "Unknown Location"}</span></p>
                </div>

                {!mechanicsResult && !loading && (
                  <button onClick={findLocalMechanics} className="px-8 py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold text-lg shadow-lg shadow-red-900/50 transition-all transform hover:scale-105 flex items-center gap-3 mx-auto">
                    <MapPin /> FIND MECHANICS NOW
                  </button>
                )}

                {loading && <div className="text-cyan-400 animate-pulse">Scanning area for service centers...</div>}

                {mechanicsResult && (
                  <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-white/5 border border-white/10 rounded-2xl p-6 text-left">
                    <h3 className="text-gray-400 text-xs uppercase tracking-widest font-bold mb-4">Search Results</h3>
                    <div className="grid gap-4">
                      {mechanicsResult.split("---").map((block, i) => {
                        if (!block.trim()) return null;
                        return (
                          <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-5 hover:bg-white/10 transition-colors shadow-lg">
                            <div className="prose prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-a:no-underline">
                              <ReactMarkdown components={{
                                a: ({ node, ...props }) => {
                                  const isMapLink = props.children?.toString().includes("Open in Google Maps");
                                  if (isMapLink) {
                                    return <a {...props} target="_blank" rel="noopener noreferrer" className="mt-3 flex items-center justify-center gap-2 w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition-all shadow-md shadow-blue-900/20 no-underline"><MapPin size={16} /> Open Location</a>;
                                  }
                                  return <a {...props} target="_blank" rel="noopener noreferrer" className="text-white hover:text-blue-400 font-bold text-lg" />;
                                }
                              }}>{block}</ReactMarkdown>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <button onClick={findLocalMechanics} className="w-full mt-6 py-3 bg-white/5 hover:bg-white/10 rounded-xl text-sm text-gray-400 transition-colors">Scan Again</button>
                  </motion.div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
