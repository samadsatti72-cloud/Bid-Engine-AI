'use client';

import React, { useState, useEffect } from 'react';
import { 
  Briefcase, 
  FolderPlus, 
  UploadCloud, 
  FileText, 
  ShieldCheck, 
  FileEdit, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  Trash2, 
  Download, 
  RefreshCw, 
  Play,
  Database,
  Search,
  ListOrdered,
  Plus
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { jsPDF } from 'jspdf';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Workspace {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface UploadedDocument {
  id: string;
  filename: string;
  file_size: number;
  created_at: string;
}

interface ExtractedRequirement {
  id: string;
  req_number: string;
  category: string;
  description: string;
  priority: string;
}

interface ComplianceResult {
  id: string;
  requirement_id: string;
  status: string;
  evidence: string;
  reasoning: string;
  gap_analysis?: string;
}

interface Capability {
  id: string;
  title: string;
  category: string;
  content: string;
  created_at: string;
}

export default function Home() {
  // App workspaces state
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [isNewWorkspaceOpen, setIsNewWorkspaceOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDesc, setNewWorkspaceDesc] = useState('');
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);

  // App documents state
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [uploading, setUploading] = useState(false);

  // RFP Requirements state
  const [requirements, setRequirements] = useState<ExtractedRequirement[]>([]);
  const [extracting, setExtracting] = useState(false);

  // Compliance state
  const [complianceResults, setComplianceResults] = useState<ComplianceResult[]>([]);
  const [validatingCompliance, setValidatingCompliance] = useState(false);

  // BGE Reranker state
  const [rankQuery, setRankQuery] = useState('');
  const [rankedRequirements, setRankedRequirements] = useState<any[]>([]);
  const [isRanking, setIsRanking] = useState(false);

  // Proposal compiler state
  const [editDraftContent, setEditDraftContent] = useState('');
  const [editStatus, setEditStatus] = useState('DRAFT');
  const [isGeneratingFullProposal, setIsGeneratingFullProposal] = useState(false);
  const [savingSection, setSavingSection] = useState(false);

  // Capability library state
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [loadingCapabilities, setLoadingCapabilities] = useState(false);
  const [seedingCapabilities, setSeedingCapabilities] = useState(false);
  const [ingestCategory, setIngestCategory] = useState('Case Study');
  const [ingestingFile, setIngestingFile] = useState(false);
  const [searchCapKeyword, setSearchCapKeyword] = useState('');
  const [selectedCapCategory, setSelectedCapCategory] = useState('ALL');

  // UI Navigation Tabs
  const [activeTab, setActiveTab] = useState<'upload' | 'capabilities' | 'compliance_hub' | 'proposal'>('upload');
  const [activeSubTab, setActiveSubTab] = useState<'requirements' | 'matrix' | 'gaps'>('requirements');
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Auto-hide banners after 5 seconds
  useEffect(() => {
    if (banner) {
      const timer = setTimeout(() => setBanner(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [banner]);

  // Initial load
  useEffect(() => {
    fetchWorkspaces();
    fetchCapabilities();
  }, []);

  // Sync workspace data
  useEffect(() => {
    if (activeWorkspaceId) {
      const ws = workspaces.find(w => w.id === activeWorkspaceId);
      if (ws) {
        setActiveWorkspace(ws);
        fetchDocuments(activeWorkspaceId);
        fetchRequirements(activeWorkspaceId);
        fetchComplianceResults(activeWorkspaceId);
        fetchProposalSections(activeWorkspaceId);
        // Reset rank state
        setRankQuery('');
        setRankedRequirements([]);
      }
    } else {
      setActiveWorkspace(null);
      setDocuments([]);
      setRequirements([]);
      setComplianceResults([]);
      setEditDraftContent('');
      setRankedRequirements([]);
    }
  }, [activeWorkspaceId, workspaces]);

  // Dynamic filter search capabilities
  useEffect(() => {
    fetchCapabilitiesWithFilters();
  }, [selectedCapCategory, searchCapKeyword]);

  const showBanner = (type: 'success' | 'error', message: string) => {
    setBanner({ type, message });
  };

  // API: Fetch workspaces
  const fetchWorkspaces = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/workspaces`);
      if (res.ok) {
        const data = await res.json();
        setWorkspaces(data);
        if (data.length > 0 && !activeWorkspaceId) {
          setActiveWorkspaceId(data[0].id);
        }
      } else {
        showBanner('error', 'Failed to load workspaces.');
      }
    } catch (err) {
      showBanner('error', 'Error connecting to backend API.');
    }
  };

  // API: Create new workspace
  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;

    try {
      setCreatingWorkspace(true);
      const res = await fetch(`${API_BASE_URL}/api/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newWorkspaceName, description: newWorkspaceDesc })
      });

      if (res.ok) {
        const data = await res.json();
        setWorkspaces(prev => [data, ...prev]);
        setActiveWorkspaceId(data.id);
        setNewWorkspaceName('');
        setNewWorkspaceDesc('');
        setIsNewWorkspaceOpen(false);
        showBanner('success', `Workspace "${data.name}" created!`);
      } else {
        showBanner('error', 'Failed to create workspace.');
      }
    } catch (err) {
      showBanner('error', 'Error creating workspace.');
    } finally {
      setCreatingWorkspace(false);
    }
  };

  // API: Fetch uploaded documents
  const fetchDocuments = async (wsId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${wsId}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      showBanner('error', 'Error loading documents.');
    }
  };

  // API: File Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeWorkspaceId) return;

    const allowedExtensions = ['.pdf', '.docx', '.doc', '.txt'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      showBanner('error', 'Only PDF, DOCX, DOC, and TXT files are supported.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      setUploading(true);
      showBanner('success', `Uploading and parsing "${file.name}"...`);
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/upload`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setDocuments(prev => [data, ...prev]);
        showBanner('success', `Successfully uploaded "${file.name}"!`);
      } else {
        const errData = await res.json();
        showBanner('error', errData.detail || 'Upload failed.');
      }
    } catch (err) {
      showBanner('error', 'Network error during upload.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // API: Fetch Extracted Requirements
  const fetchRequirements = async (wsId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${wsId}/requirements`);
      if (res.ok) {
        const data = await res.json();
        setRequirements(data);
      }
    } catch (err) {
      showBanner('error', 'Error loading requirements.');
    }
  };

  // API: Extract requirements
  const handleExtractRequirements = async () => {
    if (!activeWorkspaceId) return;

    try {
      setExtracting(true);
      showBanner('success', 'Extracting RFP checklist requirements via local AI...');
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/extract`, {
        method: 'POST'
      });

      if (res.ok) {
        const data = await res.json();
        showBanner('success', data.message || 'Requirements successfully extracted!');
        fetchRequirements(activeWorkspaceId);
      } else {
        const errData = await res.json();
        showBanner('error', errData.detail || 'Requirements extraction failed.');
      }
    } catch (err) {
      showBanner('error', 'Error calling requirements extraction API.');
    } finally {
      setExtracting(false);
    }
  };

  // API: Fetch Compliance Results
  const fetchComplianceResults = async (wsId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${wsId}/compliance/results`);
      if (res.ok) {
        const data = await res.json();
        setComplianceResults(data);
      }
    } catch (err) {
      showBanner('error', 'Error loading compliance results.');
    }
  };

  // API: Run Compliance Audit
  const handleRunCompliance = async () => {
    if (!activeWorkspaceId) return;

    try {
      setValidatingCompliance(true);
      showBanner('success', 'Starting AI compliance audit grounded against capabilities library...');
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/compliance/validate`, {
        method: 'POST'
      });

      if (res.ok) {
        const data = await res.json();
        showBanner('success', data.message || 'Compliance audit completed!');
        fetchComplianceResults(activeWorkspaceId);
      } else {
        const errData = await res.json();
        showBanner('error', errData.detail || 'Compliance audit failed.');
      }
    } catch (err) {
      showBanner('error', 'Error running compliance audit.');
    } finally {
      setValidatingCompliance(false);
    }
  };

  // API: Fetch Proposal draft
  const fetchProposalSections = async (wsId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${wsId}/proposal/sections`);
      if (res.ok) {
        const data = await res.json();
        const mainSec = data.find((s: any) => s.section_code === 'MAIN_DRAFT') || data[0];
        if (mainSec) {
          setEditDraftContent(mainSec.draft_content || '');
          setEditStatus(mainSec.status || 'DRAFT');
        }
      }
    } catch (err) {
      showBanner('error', 'Error loading proposal draft.');
    }
  };

  // API: Compile complete proposal
  const handleGenerateFullProposal = async () => {
    if (!activeWorkspaceId) return;

    try {
      setIsGeneratingFullProposal(true);
      showBanner('success', 'Compiling full proposal response. This may take up to 2 minutes on CPU...');
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/proposal/generate_full`, {
        method: 'POST'
      });

      if (res.ok) {
        const data = await res.json();
        setEditDraftContent(data.draft);
        showBanner('success', 'Full proposal response compiled successfully!');
      } else {
        const errData = await res.json();
        showBanner('error', errData.detail || 'Compilation failed.');
      }
    } catch (err) {
      showBanner('error', 'Error compiling proposal.');
    } finally {
      setIsGeneratingFullProposal(false);
    }
  };

  // API: Save proposal draft
  const handleSaveMainDraft = async () => {
    if (!activeWorkspaceId) return;

    try {
      setSavingSection(true);
      const sectionsRes = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/proposal/sections`);
      let secId = null;
      if (sectionsRes.ok) {
        const data = await sectionsRes.json();
        const mainSec = data.find((s: any) => s.section_code === 'MAIN_DRAFT');
        if (mainSec) secId = mainSec.id;
      }

      let res;
      if (secId) {
        res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/proposal/sections/${secId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ draft_content: editDraftContent, status: editStatus })
        });
      } else {
        res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/proposal/sections`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            section_title: 'Main Proposal Response',
            section_code: 'MAIN_DRAFT',
            prompt_instruction: 'Consolidated RAG Proposal Draft',
            draft_content: editDraftContent,
            status: editStatus
          })
        });
      }

      if (res.ok) {
        showBanner('success', 'Proposal saved successfully!');
      } else {
        showBanner('error', 'Failed to save proposal draft.');
      }
    } catch (err) {
      showBanner('error', 'Error saving proposal draft.');
    } finally {
      setSavingSection(false);
    }
  };

  // API: Delete proposal draft
  const handleDeleteProposal = async () => {
    if (!activeWorkspaceId) return;
    if (!confirm('Are you sure you want to delete/clear the current proposal draft?')) return;
    
    try {
      setSavingSection(true);
      const sectionsRes = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/proposal/sections`);
      let secId = null;
      if (sectionsRes.ok) {
        const data = await sectionsRes.json();
        const mainSec = data.find((s: any) => s.section_code === 'MAIN_DRAFT');
        if (mainSec) secId = mainSec.id;
      }
      
      if (secId) {
        const res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/proposal/sections/${secId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ draft_content: "", status: "DRAFT" })
        });
        if (res.ok) {
          setEditDraftContent('');
          setEditStatus('DRAFT');
          showBanner('success', 'Proposal draft cleared.');
        } else {
          showBanner('error', 'Failed to clear proposal content.');
        }
      } else {
        setEditDraftContent('');
        showBanner('success', 'Proposal draft cleared.');
      }
    } catch (err) {
      showBanner('error', 'Error clearing proposal.');
    } finally {
      setSavingSection(false);
    }
  };

  // API: Rerank requirements using BGE Ranker
  const handleRerankRequirements = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!activeWorkspaceId) return;

    try {
      setIsRanking(true);
      const res = await fetch(`${API_BASE_URL}/api/workspaces/${activeWorkspaceId}/requirements/rank`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: rankQuery })
      });

      if (res.ok) {
        const data = await res.json();
        setRankedRequirements(data);
        showBanner('success', 'Extracted requirements reranked using BGE Reranker!');
      } else {
        const errData = await res.json();
        showBanner('error', errData.detail || 'Failed to rerank requirements.');
      }
    } catch (err) {
      showBanner('error', 'Error calling requirements ranker API.');
    } finally {
      setIsRanking(false);
    }
  };

  // API: Fetch Capability Library items
  const fetchCapabilities = async () => {
    try {
      setLoadingCapabilities(true);
      const res = await fetch(`${API_BASE_URL}/api/capabilities`);
      if (res.ok) {
        const data = await res.json();
        setCapabilities(data);
      }
    } catch (err) {
      showBanner('error', 'Failed to load Capability Library.');
    } finally {
      setLoadingCapabilities(false);
    }
  };

  // API: Fetch Capability Library items with filters
  const fetchCapabilitiesWithFilters = async () => {
    try {
      setLoadingCapabilities(true);
      let url = `${API_BASE_URL}/api/capabilities`;
      const params = [];
      if (selectedCapCategory && selectedCapCategory !== 'ALL') {
        params.push(`category=${encodeURIComponent(selectedCapCategory)}`);
      }
      if (searchCapKeyword.trim()) {
        params.push(`search=${encodeURIComponent(searchCapKeyword)}`);
      }
      if (params.length > 0) {
        url += `?${params.join('&')}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setCapabilities(data);
      }
    } catch (err) {
      showBanner('error', 'Error filtering capability library.');
    } finally {
      setLoadingCapabilities(false);
    }
  };

  // API: Ingest capability file
  const handleIngestCapabilityFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIngestingFile(true);
      showBanner('success', `Ingesting "${file.name}" into Capability Library...`);
      
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await fetch(`${API_BASE_URL}/api/capabilities/ingest?category=${encodeURIComponent(ingestCategory)}`, {
        method: 'POST',
        body: formData
      });
      
      if (res.ok) {
        showBanner('success', `Successfully ingested "${file.name}"!`);
        fetchCapabilities();
      } else {
        const errData = await res.json();
        showBanner('error', errData.detail || 'Failed to ingest file.');
      }
    } catch (err) {
      showBanner('error', 'Error connecting to server during ingestion.');
    } finally {
      setIngestingFile(false);
      e.target.value = '';
    }
  };

  // API: Seed Capability Library
  const handleSeedCapabilities = async () => {
    try {
      setSeedingCapabilities(true);
      showBanner('success', 'Seeding library with 50 preloaded past projects & certifications...');
      const res = await fetch(`${API_BASE_URL}/api/capabilities/seed`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        showBanner('success', data.message || 'Capability Library seeded!');
        fetchCapabilities();
      } else {
        showBanner('error', 'Seeding failed.');
      }
    } catch (err) {
      showBanner('error', 'Error seeding capability database.');
    } finally {
      setSeedingCapabilities(false);
    }
  };

  // API: Reset Capability Library
  const handleResetCapabilities = async () => {
    if (!confirm('Are you sure you want to clear the Capability Library?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/capabilities/reset`, { method: 'DELETE' });
      if (res.ok) {
        showBanner('success', 'Capability Library cleared.');
        setCapabilities([]);
      }
    } catch (err) {
      showBanner('error', 'Error resetting capability database.');
    }
  };

  // Export proposal response as PDF file
  const handleDownloadPDF = () => {
    if (!editDraftContent.trim()) {
      showBanner('error', 'No proposal content generated to download!');
      return;
    }

    try {
      const doc = new jsPDF({
        orientation: 'p',
        unit: 'mm',
        format: 'a4',
      });
      
      const pageHeight = doc.internal.pageSize.height;
      const pageWidth = doc.internal.pageSize.width;
      const margin = 20; // 20mm margins
      const contentWidth = pageWidth - (margin * 2);
      
      let cursorY = 22; // Start below the header space
      const lineHeight = 6.5;
      const paragraphSpacing = 5.0;
      
      // Helper function for adding content lines and handling pages
      const addText = (text: string, isHeading: boolean, headingLevel: number = 2) => {
        if (isHeading) {
          doc.setFont('helvetica', 'bold');
          if (headingLevel === 1) {
            doc.setFontSize(15);
          } else if (headingLevel === 2) {
            doc.setFontSize(13);
          } else {
            doc.setFontSize(11.5);
          }
        } else {
          doc.setFont('helvetica', 'normal');
          doc.setFontSize(10.5);
        }
        
        // Split text by manual newline to preserve bullet points or lists
        const lines = text.split('\n');
        for (let line of lines) {
          const textLines = doc.splitTextToSize(line, contentWidth);
          for (let wrappedLine of textLines) {
            if (cursorY + lineHeight > pageHeight - 20) {
              doc.addPage();
              cursorY = 22; // reset cursor leaving space for top header
            }
            doc.text(wrappedLine, margin, cursorY);
            cursorY += lineHeight;
          }
        }
      };

      // Add cover/title information on page 1
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(18);
      doc.text("Bid Proposal Response", margin, cursorY);
      cursorY += 10;
      
      doc.setFontSize(10.5);
      doc.setFont('helvetica', 'normal');
      doc.text(`Workspace: ${activeWorkspace?.name || 'N/A'}`, margin, cursorY);
      cursorY += 6;
      doc.text(`Date Generated: ${new Date().toLocaleDateString()}`, margin, cursorY);
      cursorY += 8;
      
      // Line divider
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.line(margin, cursorY, pageWidth - margin, cursorY);
      cursorY += 12; // Extra space after divider
      
      // Split the draft content by double newlines to handle paragraph blocks
      const blocks = editDraftContent.split(/\n\s*\n/);
      
      for (let block of blocks) {
        const cleanBlock = block.trim();
        if (!cleanBlock) continue;
        
        // Match Markdown Headers
        if (cleanBlock.startsWith('# ')) {
          addText(cleanBlock.replace(/^#\s+/, ''), true, 1);
          cursorY += paragraphSpacing;
        } else if (cleanBlock.startsWith('## ')) {
          addText(cleanBlock.replace(/^##\s+/, ''), true, 2);
          cursorY += paragraphSpacing;
        } else if (cleanBlock.startsWith('### ')) {
          addText(cleanBlock.replace(/^###\s+/, ''), true, 3);
          cursorY += paragraphSpacing;
        } else {
          // Standard paragraph
          addText(cleanBlock, false);
          cursorY += paragraphSpacing;
        }
      }
      
      // Post-process all pages to inject elegant Header and Footer lines + page numbers
      const pageCount = doc.getNumberOfPages();
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        
        // Top Header
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(8.5);
        doc.setTextColor(148, 163, 184); // slate-400
        doc.text(`Bid Proposal Response — Workspace: ${activeWorkspace?.name || 'N/A'}`, margin, 12);
        doc.setDrawColor(226, 232, 240);
        doc.setLineWidth(0.25);
        doc.line(margin, 15, pageWidth - margin, 15);
        
        // Bottom Footer
        doc.line(margin, pageHeight - 15, pageWidth - margin, pageHeight - 15);
        doc.text(`Generated on ${new Date().toLocaleDateString()}`, margin, pageHeight - 10);
        doc.text(`Page ${i} of ${pageCount}`, pageWidth - margin - 20, pageHeight - 10);
      }
      
      doc.save(`${activeWorkspace?.name || 'proposal'}_response.pdf`);
      showBanner('success', 'PDF downloaded successfully!');
    } catch (err) {
      showBanner('error', 'Error generating PDF document.');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'PASS':
      case 'COMPLIANT':
        return <span className="px-3 py-1 rounded-md text-xs font-extrabold bg-emerald-50 text-emerald-700 border border-emerald-200">PASS</span>;
      case 'PARTIAL':
      case 'PARTIALLY-COMPLIANT':
        return <span className="px-3 py-1 rounded-md text-xs font-extrabold bg-amber-50 text-amber-700 border border-amber-200">PARTIAL</span>;
      case 'FAIL':
      case 'NON-COMPLIANT':
        return <span className="px-3 py-1 rounded-md text-xs font-extrabold bg-rose-50 text-rose-700 border border-rose-200">FAIL</span>;
      default:
        return <span className="px-3 py-1 rounded-md text-xs font-extrabold bg-slate-50 text-slate-600 border border-slate-200">UNSURE</span>;
    }
  };

  // Filter complianceResults to find gaps (FAIL/PARTIAL status)
  const complianceGaps = complianceResults.filter(
    r => r.status.toUpperCase() === 'FAIL' || r.status.toUpperCase() === 'PARTIAL'
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans flex flex-col antialiased">
      {/* Banner */}
      {banner && (
        <div className={`fixed top-4 right-4 z-50 p-4 rounded-xl shadow-lg flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-300 border text-sm ${
          banner.type === 'success' 
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
            : 'bg-rose-50 border-rose-200 text-rose-800'
        }`}>
          {banner.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : <AlertCircle className="w-5 h-5 text-rose-600" />}
          <span className="font-semibold">{banner.message}</span>
        </div>
      )}

      {/* Header Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40 px-6 py-4 shadow-sm shrink-0">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-black text-2xl text-slate-900 tracking-tight leading-tight">BidEngine AI</h1>
              <p className="text-sm text-slate-500 font-semibold mt-0.5">Response Compiler Workspace</p>
            </div>
          </div>

          {/* Active Workspace Selector */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-600">Workspace:</span>
            <select
              value={activeWorkspaceId || ''}
              onChange={e => setActiveWorkspaceId(e.target.value || null)}
              className="bg-white border border-slate-200 text-slate-800 text-sm font-bold rounded-lg px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">-- Select Workspace --</option>
              {workspaces.map(ws => (
                <option key={ws.id} value={ws.id}>{ws.name}</option>
              ))}
            </select>
            <Button
              onClick={() => setIsNewWorkspaceOpen(true)}
              variant="outline"
              className="rounded-lg h-9 px-3 text-sm font-semibold flex items-center gap-1.5 border-slate-200 text-slate-700 bg-white"
            >
              <FolderPlus className="w-4 h-4" />
              New
            </Button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs - Exactly 4 Tabs */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 shrink-0">
        <div className="max-w-7xl mx-auto flex flex-wrap gap-2 md:gap-4">
          <button
            onClick={() => setActiveTab('upload')}
            className={`px-5 py-2.5 text-sm font-semibold rounded-xl transition-all flex items-center gap-2 border ${
              activeTab === 'upload' 
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-sm' 
                : 'text-slate-500 hover:text-slate-800 border-transparent hover:bg-slate-50'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            1. RFP Documents
          </button>
          <button
            onClick={() => setActiveTab('capabilities')}
            className={`px-5 py-2.5 text-sm font-semibold rounded-xl transition-all flex items-center gap-2 border ${
              activeTab === 'capabilities' 
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-sm' 
                : 'text-slate-500 hover:text-slate-800 border-transparent hover:bg-slate-50'
            }`}
          >
            <Database className="w-4 h-4" />
            2. Capability Database
          </button>
          <button
            onClick={() => setActiveTab('compliance_hub')}
            className={`px-5 py-2.5 text-sm font-semibold rounded-xl transition-all flex items-center gap-2 border ${
              activeTab === 'compliance_hub' 
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-sm' 
                : 'text-slate-500 hover:text-slate-800 border-transparent hover:bg-slate-50'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            3. Compliance & Requirements Hub
          </button>
          <button
            onClick={() => setActiveTab('proposal')}
            className={`px-5 py-2.5 text-sm font-semibold rounded-xl transition-all flex items-center gap-2 border ${
              activeTab === 'proposal' 
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-sm' 
                : 'text-slate-500 hover:text-slate-800 border-transparent hover:bg-slate-50'
            }`}
          >
            <FileEdit className="w-4 h-4" />
            4. AI Proposal Workspace
          </button>
        </div>
      </div>

      {/* Main Workspace Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-6 overflow-hidden flex flex-col">
        {!activeWorkspaceId ? (
          <Card className="border-slate-200 shadow-sm bg-white p-8 text-center my-12 max-w-md mx-auto rounded-2xl">
            <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-slate-800 font-extrabold text-lg">No Active Workspace Selected</h3>
            <p className="text-sm text-slate-500 mt-2 leading-relaxed">
              Please choose a workspace from the dropdown list in the header, or click "New" to create a new workspace.
            </p>
          </Card>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            
            {/* TAB 1: RFP DOCUMENTS */}
            {activeTab === 'upload' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-y-auto">
                <Card className="border-slate-200 shadow-sm bg-white rounded-2xl h-fit">
                  <CardHeader className="pb-4">
                    <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <UploadCloud className="w-5 h-5 text-indigo-600" />
                      Upload Tender RFP
                    </CardTitle>
                    <CardDescription className="text-sm text-slate-500 mt-1">
                      Upload RFP documents (.pdf, .docx, .doc, .txt) to extract requirements checklists.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="border-2 border-dashed border-slate-200 rounded-xl p-10 text-center hover:border-indigo-400 transition-colors bg-slate-50/50 relative cursor-pointer">
                      <input
                        type="file"
                        onChange={handleFileUpload}
                        disabled={uploading}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        accept=".pdf,.docx,.doc,.txt"
                      />
                      <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                      <p className="text-base font-bold text-slate-700">Click to upload RFP file</p>
                      <p className="text-sm text-slate-400 mt-1">PDF, DOCX, DOC, or TXT up to 20MB</p>
                    </div>

                    {uploading && (
                      <div className="flex items-center justify-center gap-2 text-sm font-semibold text-indigo-600 py-3 bg-indigo-50 rounded-xl">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Parsing document contents...
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="lg:col-span-2 border-slate-200 shadow-sm bg-white rounded-2xl flex flex-col h-full overflow-hidden">
                  <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100 pb-4 shrink-0">
                    <div>
                      <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                        <FileText className="w-5 h-5 text-indigo-600" />
                        RFP Document List ({documents.length})
                      </CardTitle>
                      <CardDescription className="text-sm text-slate-500 mt-1">
                        Uploaded documents currently active in this workspace.
                      </CardDescription>
                    </div>
                    {documents.length > 0 && (
                      <Button
                        onClick={handleExtractRequirements}
                        disabled={extracting}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm h-10 px-5 rounded-lg flex items-center gap-1.5 shadow-sm border-0"
                      >
                        {extracting ? (
                          <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            Extracting...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 fill-current" />
                            Extract Requirements
                          </>
                        )}
                      </Button>
                    )}
                  </CardHeader>
                  <CardContent className="flex-1 p-0 overflow-y-auto">
                    {documents.length === 0 ? (
                      <div className="text-center py-20 text-slate-400 text-sm">
                        No documents uploaded yet. Upload your first tender RFP file in the left panel.
                      </div>
                    ) : (
                      <Table>
                        <TableHeader className="bg-slate-50/80 sticky top-0 z-10">
                          <TableRow>
                            <TableHead className="text-sm font-bold text-slate-700 py-3.5 pl-6">Filename</TableHead>
                            <TableHead className="text-sm font-bold text-slate-700 py-3.5">Size</TableHead>
                            <TableHead className="text-sm font-bold text-slate-700 py-3.5 pr-6">Uploaded At</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {documents.map(doc => (
                            <TableRow key={doc.id} className="hover:bg-slate-50/50">
                              <TableCell className="text-sm font-semibold text-slate-900 py-4 pl-6">{doc.filename}</TableCell>
                              <TableCell className="text-sm text-slate-600 py-4">{(doc.file_size / 1024).toFixed(1)} KB</TableCell>
                              <TableCell className="text-sm text-slate-600 py-4 pr-6">{new Date(doc.created_at).toLocaleString()}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {/* TAB 2: BIDDER CAPABILITY DATABASE */}
            {activeTab === 'capabilities' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-y-auto">
                {/* Upload capabilities */}
                <Card className="border-slate-200 shadow-sm bg-white rounded-2xl h-fit">
                  <CardHeader className="pb-4">
                    <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <Database className="w-5 h-5 text-indigo-600" />
                      Add Files to Database
                    </CardTitle>
                    <CardDescription className="text-sm text-slate-500 mt-1">
                      Upload past project case studies, cv summaries, or certifications to ground your bid response.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-slate-700 block">Select Document Category</label>
                      <select
                        value={ingestCategory}
                        onChange={e => setIngestCategory(e.target.value)}
                        className="w-full bg-white border border-slate-200 text-slate-800 text-sm font-semibold rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="Case Study">Case Study</option>
                        <option value="Certification">Certification</option>
                        <option value="Resume">Resume</option>
                        <option value="Company Profile">Company Profile</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>

                    <div className="border-2 border-dashed border-slate-200 rounded-xl p-10 text-center hover:border-indigo-400 transition-colors bg-slate-50/50 relative cursor-pointer">
                      <input
                        type="file"
                        onChange={handleIngestCapabilityFile}
                        disabled={ingestingFile}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        accept=".pdf,.docx,.doc,.txt"
                      />
                      <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                      <p className="text-base font-bold text-slate-700">Click to ingest capability file</p>
                      <p className="text-sm text-slate-400 mt-1">PDF, DOCX, or TXT (auto-chunked)</p>
                    </div>

                    {ingestingFile && (
                      <div className="flex items-center justify-center gap-2 text-sm font-semibold text-indigo-600 py-3 bg-indigo-50 rounded-xl">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Extracting metadata & chunking...
                      </div>
                    )}

                    <hr className="border-slate-100" />
                    
                    {/* Database Seeding controls */}
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-slate-700 block">Quick Administration</label>
                      <div className="grid grid-cols-2 gap-2">
                        <Button
                          onClick={handleSeedCapabilities}
                          disabled={seedingCapabilities}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm h-10 rounded-lg border-0 shadow-sm"
                        >
                          {seedingCapabilities ? 'Seeding...' : 'Seed 50 Records'}
                        </Button>
                        <Button
                          onClick={handleResetCapabilities}
                          variant="outline"
                          className="border-slate-200 text-slate-600 hover:bg-rose-50 hover:text-rose-700 font-semibold text-sm h-10 rounded-lg"
                        >
                          Wipe Database
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Capability records list */}
                <Card className="lg:col-span-2 border-slate-200 shadow-sm bg-white rounded-2xl flex flex-col h-full overflow-hidden">
                  <CardHeader className="border-b border-slate-100 pb-4 shrink-0">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                          <Database className="w-5 h-5 text-indigo-600" />
                          Corporate Capabilities ({capabilities.length})
                        </CardTitle>
                        <CardDescription className="text-sm text-slate-500 mt-1">
                          Grounded past evidence records loaded in the system database.
                        </CardDescription>
                      </div>
                      
                      {/* Search / Filters */}
                      <div className="flex items-center gap-3 shrink-0">
                        <select
                          value={selectedCapCategory}
                          onChange={e => setSelectedCapCategory(e.target.value)}
                          className="bg-white border border-slate-200 text-slate-800 text-sm font-semibold rounded-lg px-3 py-1.5 h-9 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
                        >
                          <option value="ALL">ALL Categories</option>
                          <option value="Case Study">Case Study</option>
                          <option value="Certification">Certification</option>
                          <option value="Resume">Resume</option>
                          <option value="Company Profile">Company Profile</option>
                          <option value="Other">Other</option>
                        </select>
                        <div className="relative w-48">
                          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                          <Input
                            value={searchCapKeyword}
                            onChange={e => setSearchCapKeyword(e.target.value)}
                            placeholder="Search keywords..."
                            className="pl-9 h-9 bg-white border-slate-200 text-sm rounded-lg placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  
                  <CardContent className="flex-1 p-0 overflow-y-auto">
                    {loadingCapabilities ? (
                      <div className="text-center py-20 text-slate-400 text-sm flex items-center justify-center gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" />
                        Loading database records...
                      </div>
                    ) : capabilities.length === 0 ? (
                      <div className="text-center py-20 text-slate-400 text-sm">
                        No capability records found. Seed the database or upload custom files.
                      </div>
                    ) : (
                      <Table>
                        <TableHeader className="bg-slate-50/80 sticky top-0 z-10">
                          <TableRow>
                            <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-48 pl-6">Record Title</TableHead>
                            <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-32">Category</TableHead>
                            <TableHead className="text-sm font-bold text-slate-700 py-3.5 pr-6">Snippet Content</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {capabilities.map(cap => (
                            <TableRow key={cap.id} className="hover:bg-slate-50/50 align-top">
                              <TableCell className="text-sm font-semibold text-slate-900 py-4 pl-6 leading-snug">{cap.title}</TableCell>
                              <TableCell className="text-sm py-4">
                                <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${
                                  cap.category === 'Certification' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' :
                                  cap.category === 'Case Study' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' :
                                  'bg-slate-100 text-slate-600'
                                }`}>
                                  {cap.category}
                                </span>
                              </TableCell>
                              <TableCell className="text-sm text-slate-600 py-4 pr-6 leading-relaxed max-w-xl select-text whitespace-pre-wrap">{cap.content}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {/* TAB 3: COMPLIANCE & REQUIREMENTS HUB WITH SUB-TABS */}
            {activeTab === 'compliance_hub' && (
              <div className="flex flex-col gap-6 flex-1 overflow-hidden">
                {/* Audit & Subnavigation Bar */}
                <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
                  {/* Sub-tabs switchers */}
                  <div className="flex gap-2 bg-slate-100 p-1.5 rounded-xl w-fit">
                    <button
                      onClick={() => setActiveSubTab('requirements')}
                      className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
                        activeSubTab === 'requirements' 
                          ? 'bg-white text-indigo-700 shadow-sm font-bold' 
                          : 'text-slate-500 hover:text-slate-850 hover:bg-slate-200/50'
                      }`}
                    >
                      A. RFP Requirements (BGE Reranker)
                    </button>
                    <button
                      onClick={() => setActiveSubTab('matrix')}
                      className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
                        activeSubTab === 'matrix' 
                          ? 'bg-white text-indigo-700 shadow-sm font-bold' 
                          : 'text-slate-500 hover:text-slate-850 hover:bg-slate-200/50'
                      }`}
                    >
                      B. Compliance Matrix Table
                    </button>
                    <button
                      onClick={() => setActiveSubTab('gaps')}
                      className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
                        activeSubTab === 'gaps' 
                          ? 'bg-white text-indigo-700 shadow-sm font-bold' 
                          : 'text-slate-500 hover:text-slate-850 hover:bg-slate-200/50'
                      }`}
                    >
                      C. Warning Gaps Cards
                    </button>
                  </div>

                  {/* Validate Trigger */}
                  <div>
                    {requirements.length > 0 ? (
                      <Button
                        onClick={handleRunCompliance}
                        disabled={validatingCompliance}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm h-10 px-5 rounded-lg flex items-center gap-1.5 shadow-sm border-0"
                      >
                        {validatingCompliance ? (
                          <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            Evaluating requirements...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 fill-current" />
                            Run Compliance Audit
                          </>
                        )}
                      </Button>
                    ) : (
                      <span className="text-sm text-slate-400 font-semibold italic bg-slate-50 px-3.5 py-1.5 rounded-lg border border-slate-100">
                        No checklist extracted. First, upload an RFP and click Extract.
                      </span>
                    )}
                  </div>
                </div>

                {/* Sub-tab Rendering */}
                <div className="flex-1 flex flex-col overflow-hidden">
                  
                  {/* SUB-TAB A: RFP REQUIREMENTS BGE RERANKER */}
                  {activeSubTab === 'requirements' && (
                    <div className="flex flex-col gap-4 flex-1 overflow-hidden">
                      <Card className="border-slate-200 shadow-sm bg-white rounded-2xl p-4 shrink-0">
                        <form onSubmit={handleRerankRequirements} className="flex gap-3">
                          <div className="flex-1 relative">
                            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                            <Input
                              value={rankQuery}
                              onChange={e => setRankQuery(e.target.value)}
                              placeholder="Enter search query to rerank RFP requirements (e.g. 'security', 'experience', 'ISO')..."
                              className="pl-10 h-10 bg-white border-slate-200 focus:border-indigo-500 text-slate-850 placeholder:text-slate-400 text-sm rounded-lg shadow-sm"
                            />
                          </div>
                          <Button
                            type="submit"
                            disabled={isRanking || requirements.length === 0}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm h-10 px-5 rounded-lg border-0 shadow-sm flex items-center gap-1.5 shrink-0"
                          >
                            {isRanking ? (
                              <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                Reranking...
                              </>
                            ) : (
                              <>
                                <ListOrdered className="w-4 h-4" />
                                Rerank via BGE
                              </>
                            )}
                          </Button>
                        </form>
                      </Card>

                      <Card className="flex-1 border-slate-200 shadow-sm bg-white rounded-2xl flex flex-col overflow-hidden">
                        <CardHeader className="bg-slate-50/50 border-b border-slate-100 py-4 px-6 shrink-0 flex flex-row items-center justify-between">
                          <div>
                            <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                              <ListOrdered className="w-4 h-4 text-indigo-600" />
                              Extracted RFP Requirements Checklist ({rankedRequirements.length > 0 ? rankedRequirements.length : requirements.length})
                            </CardTitle>
                          </div>
                          {rankedRequirements.length > 0 && (
                            <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 px-3 py-1 rounded-full uppercase tracking-wider">
                              BGE-TinyBERT Model Reranked
                            </span>
                          )}
                        </CardHeader>
                        <CardContent className="flex-1 p-0 overflow-y-auto">
                          {requirements.length === 0 ? (
                            <div className="text-center py-20 text-slate-400 text-sm">
                              No RFP requirements loaded. Go to "1. RFP Documents" and extract requirements first.
                            </div>
                          ) : rankedRequirements.length === 0 ? (
                            // Default list
                            <Table>
                              <TableHeader className="bg-slate-50/80 sticky top-0 z-10">
                                <TableRow>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 pl-6 w-24">Req #</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-44">Category</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5">RFP Requirement Description</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-28 text-center pr-6">Priority</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {requirements.map(req => (
                                  <TableRow key={req.id} className="hover:bg-slate-50/50 align-top">
                                    <TableCell className="text-sm font-bold text-slate-900 py-4 pl-6">{req.req_number}</TableCell>
                                    <TableCell className="text-sm font-semibold text-slate-600 py-4">{req.category}</TableCell>
                                    <TableCell className="text-sm text-slate-800 py-4 leading-relaxed select-text pr-4">{req.description}</TableCell>
                                    <TableCell className="text-sm text-center py-4 pr-6">
                                      <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase ${
                                        req.priority === 'MUST' ? 'bg-rose-50 text-rose-700 border border-rose-100' :
                                        req.priority === 'SHOULD' ? 'bg-amber-50 text-amber-700 border border-amber-100' :
                                        'bg-slate-100 text-slate-500'
                                      }`}>
                                        {req.priority}
                                      </span>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          ) : (
                            // Ranked list
                            <Table>
                              <TableHeader className="bg-slate-50/80 sticky top-0 z-10">
                                <TableRow>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 pl-6 w-20 text-center">Rank</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-24">Req #</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-36">BGE Score</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-36">Category</TableHead>
                                  <TableHead className="text-sm font-bold text-slate-700 py-3.5 pr-6">RFP Requirement Description</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {rankedRequirements.map((req, idx) => (
                                  <TableRow key={req.id} className="hover:bg-slate-50/50 align-middle">
                                    <TableCell className="text-sm font-bold text-indigo-600 text-center py-4 pl-6">{idx + 1}</TableCell>
                                    <TableCell className="text-sm font-bold text-slate-900 py-4">{req.req_number}</TableCell>
                                    <TableCell className="py-4">
                                      <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-slate-805">
                                          {req.score.toFixed(4)}
                                        </span>
                                        <div className="w-16 bg-slate-100 h-1.5 rounded-full overflow-hidden border border-slate-200">
                                          <div 
                                            className="bg-indigo-600 h-full rounded-full" 
                                            style={{ width: `${Math.max(0, Math.min(100, req.score * 100))}%` }}
                                          ></div>
                                        </div>
                                      </div>
                                    </TableCell>
                                    <TableCell className="text-xs font-semibold text-slate-650 py-4">{req.category}</TableCell>
                                    <TableCell className="text-sm text-slate-800 py-4 leading-relaxed select-text pr-6">{req.description}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  {/* SUB-TAB B: COMPLIANCE MATRIX TABLE */}
                  {activeSubTab === 'matrix' && (
                    <Card className="flex-1 border-slate-200 shadow-sm bg-white rounded-2xl flex flex-col overflow-hidden h-full">
                      <CardContent className="flex-1 p-0 overflow-y-auto">
                        {requirements.length === 0 ? (
                          <div className="text-center py-20 text-slate-400 text-sm">
                            No checklist requirements loaded. Go to "1. RFP Documents" and extract requirements.
                          </div>
                        ) : (
                          <Table>
                            <TableHeader className="bg-slate-50/80 sticky top-0 z-10">
                              <TableRow>
                                <TableHead className="text-sm font-bold text-slate-700 py-3.5 pl-6 w-20">Req #</TableHead>
                                <TableHead className="text-sm font-bold text-slate-700 py-3.5 max-w-sm">Requirement Description</TableHead>
                                <TableHead className="text-sm font-bold text-slate-700 py-3.5 w-28">Status</TableHead>
                                <TableHead className="text-sm font-bold text-slate-700 py-3.5 pr-6">Matched Evidence Quote</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {requirements.map(req => {
                                const result = complianceResults.find(r => r.requirement_id === req.id);
                                return (
                                  <TableRow key={req.id} className="hover:bg-slate-50/50 align-top">
                                    <TableCell className="text-sm font-bold text-slate-900 py-4 pl-6">{req.req_number}</TableCell>
                                    <TableCell className="text-sm text-slate-800 font-medium py-4 leading-relaxed max-w-sm pr-4 select-text">{req.description}</TableCell>
                                    <TableCell className="py-4">
                                      {result ? getStatusBadge(result.status) : <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-400 border border-slate-200">Not Audited</span>}
                                    </TableCell>
                                    <TableCell className="text-sm text-slate-700 leading-relaxed max-w-md py-4 pr-6 select-text">
                                      {result ? (
                                        result.status.toUpperCase() === 'FAIL' ? (
                                          <span className="text-rose-500 font-medium italic">Missing corporate evidence context.</span>
                                        ) : (
                                          <div className="bg-slate-50/70 border border-slate-200/60 p-4 rounded-xl leading-relaxed whitespace-pre-wrap select-text shadow-sm">
                                            <p className="font-extrabold text-indigo-750 text-xs mb-1.5 uppercase tracking-wider">Matched Library Citation:</p>
                                            <p className="opacity-95 text-slate-700">{result.evidence}</p>
                                          </div>
                                        )
                                      ) : (
                                        <span className="text-slate-400 italic">Audit compliance to map evidence</span>
                                      )}
                                    </TableCell>
                                  </TableRow>
                                );
                              })}
                            </TableBody>
                          </Table>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* SUB-TAB C: WARNING GAPS CARDS */}
                  {activeSubTab === 'gaps' && (
                    <Card className="flex-1 border-slate-200 shadow-sm bg-white rounded-2xl flex flex-col overflow-hidden h-full">
                      <CardContent className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                        {complianceResults.length === 0 ? (
                          <div className="text-center py-20 text-slate-400 text-sm">
                            Run Compliance Audit to scan for gaps.
                          </div>
                        ) : complianceGaps.length === 0 ? (
                          <div className="text-center py-16 text-emerald-600 font-bold text-sm flex flex-col items-center gap-2">
                            <CheckCircle2 className="w-10 h-10 text-emerald-500 animate-bounce" />
                            No gaps found! 100% compliant with library evidence.
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {complianceGaps.map(gap => {
                              const req = requirements.find(r => r.id === gap.requirement_id);
                              const isFail = gap.status.toUpperCase() === 'FAIL';
                              return (
                                <div 
                                  key={gap.id} 
                                  className={`p-5 rounded-2xl border flex flex-col gap-4 transition-all hover:shadow-md ${
                                    isFail 
                                      ? 'bg-rose-50/50 border-rose-200/50 shadow-sm shadow-rose-50' 
                                      : 'bg-amber-50/40 border-amber-200/50 shadow-sm shadow-amber-50'
                                  }`}
                                >
                                  <div className="flex items-center justify-between border-b border-slate-200/40 pb-2.5">
                                    <span className="text-xs font-bold text-slate-500">
                                      {req?.req_number || 'EXT'} ({req?.category || 'RFP'})
                                    </span>
                                    <span className={`text-xs font-extrabold px-2.5 py-1 rounded-md ${
                                      isFail ? 'bg-rose-100 text-rose-800 border border-rose-200/30' : 'bg-amber-100 text-amber-800 border border-amber-200/30'
                                    }`}>
                                      {gap.status}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-xs font-extrabold text-slate-400 uppercase tracking-wider block mb-1">RFP Requirement:</span>
                                    <p className="text-sm font-bold text-slate-900 leading-relaxed select-text">
                                      {req?.description}
                                    </p>
                                  </div>
                                  <div className="text-sm text-slate-700 bg-white border border-slate-250/60 rounded-xl p-4 leading-relaxed shadow-sm">
                                    <strong className="text-slate-805 block mb-1.5 font-extrabold text-xs uppercase tracking-wider text-indigo-700">Gap Analysis Remediation:</strong>
                                    <p className="select-text whitespace-pre-wrap">
                                      {gap.gap_analysis && gap.gap_analysis.toLowerCase() !== 'none' 
                                        ? gap.gap_analysis 
                                        : gap.reasoning || "Missing appropriate capabilities record in corporate library."}
                                    </p>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                </div>
              </div>
            )}            {/* TAB 4: AI PROPOSAL WORKSPACE (EDIT, DELETE, PDF DOWNLOAD) */}
            {activeTab === 'proposal' && (
              <div className="flex flex-col gap-6 flex-1 overflow-hidden h-full">
                
                {/* Controls and Exporter */}
                <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
                  <div>
                    <h3 className="font-extrabold text-slate-900 text-base flex items-center gap-1.5">
                      <Sparkles className="w-5 h-5 text-indigo-600" />
                      Grounded AI Proposal Workspace
                    </h3>
                    <p className="text-sm text-slate-500 mt-1">
                      Compile, manually edit, delete, or download the grounded proposal as a formatted PDF.
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <Button
                      onClick={handleGenerateFullProposal}
                      disabled={isGeneratingFullProposal || requirements.length === 0}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm h-10 px-5 rounded-lg shadow-sm border-0 flex items-center gap-1.5"
                    >
                      {isGeneratingFullProposal ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Compiling Draft (May take 2m)...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          Compile Proposal
                        </>
                      )}
                    </Button>
                    
                    <Button
                      onClick={handleSaveMainDraft}
                      disabled={savingSection || !editDraftContent.trim()}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm h-10 px-5 rounded-lg shadow-sm border-0"
                    >
                      {savingSection ? 'Saving...' : 'Save Draft'}
                    </Button>
                    
                    <Button
                      onClick={handleDeleteProposal}
                      disabled={savingSection || !editDraftContent.trim()}
                      className="bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold text-sm h-10 px-5 rounded-lg border border-rose-200"
                    >
                      Delete Draft
                    </Button>

                    <Button
                      onClick={handleDownloadPDF}
                      disabled={!editDraftContent.trim()}
                      className="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-sm h-10 px-5 rounded-lg border border-indigo-200 flex items-center gap-1.5"
                    >
                      <Download className="w-4 h-4" />
                      Download PDF
                    </Button>
                  </div>
                </div>

                {/* Split text area editor */}
                <Card className="flex-1 border-slate-200 shadow-sm bg-slate-100 flex flex-col overflow-hidden h-full rounded-2xl">
                  <div className="px-6 py-3.5 border-b border-slate-200 bg-white flex items-center justify-between shrink-0">
                    <span className="text-sm font-bold text-slate-900">Proposal Document Editor</span>
                    <div className="flex items-center gap-2.5 text-sm text-slate-600">
                      <span className="font-semibold">Review Status:</span>
                      <select
                        value={editStatus}
                        onChange={e => setEditStatus(e.target.value)}
                        className="bg-white border border-slate-200 rounded-lg text-sm font-bold py-1 px-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
                      >
                        <option value="DRAFT">DRAFT</option>
                        <option value="UNDER-REVIEW">UNDER REVIEW</option>
                        <option value="APPROVED">APPROVED</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex-1 p-6 md:p-10 overflow-y-auto custom-scrollbar flex flex-col items-center bg-slate-100">
                    {isGeneratingFullProposal ? (
                      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-slate-400 py-20 text-center bg-white border border-slate-200 shadow-lg w-full max-w-4xl min-h-[750px] p-12 rounded-xl">
                        <RefreshCw className="w-12 h-12 animate-spin text-indigo-500" />
                        <div>
                          <p className="text-lg font-bold text-slate-800">RAG Grounded Compiler Active</p>
                          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
                            The local AI model is evaluating compliance results and drafting your proposal. This process involves multiple prompt sequences and may take up to 2 minutes on CPU.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="flex-1 w-full max-w-4xl flex flex-col gap-5 overflow-hidden h-full bg-white border border-slate-200 shadow-lg p-10 md:p-14 min-h-[842px] rounded-xl">
                        {/* Warnings if gaps exist */}
                        {editDraftContent && editDraftContent.toUpperCase().includes('FLAG:') && (
                          <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-xl flex items-start gap-3 shrink-0 shadow-sm animate-pulse">
                            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
                            <div>
                              <strong className="font-extrabold block text-sm">Anti-Hallucination Guard: Missing Evidence Flagged</strong>
                              <p className="mt-0.5 text-slate-700 leading-relaxed">
                                The AI compiler identified requirements that lack matching corporate evidence and inserted warning placeholders (e.g. <code>[FLAG: ...]</code>) inside the text. Please audit these before finalizing.
                              </p>
                            </div>
                          </div>
                        )}

                        <textarea
                          value={editDraftContent}
                          onChange={e => setEditDraftContent(e.target.value)}
                          placeholder="Your generated proposal will appear here. You can manually edit, review, or erase the contents directly in this workspace..."
                          className="flex-1 w-full p-0 border-0 text-base font-normal leading-relaxed text-slate-800 bg-white focus:outline-none resize-none select-text custom-scrollbar"
                          style={{ minHeight: '600px' }}
                        />
                      </div>
                    )}
                  </div>
                  
                  <div className="px-5 py-2.5 bg-slate-50 border-t border-slate-100 flex justify-between text-xs text-slate-400 shrink-0">
                    <span>Words: {editDraftContent ? editDraftContent.split(/\s+/).filter(Boolean).length : 0}</span>
                    <span>Characters: {editDraftContent?.length || 0}</span>
                  </div>
                </Card>

              </div>
            )}

          </div>
        )}
      </main>

      {/* CREATE WORKSPACE DIALOG */}
      <Dialog open={isNewWorkspaceOpen} onOpenChange={setIsNewWorkspaceOpen}>
        <DialogContent className="bg-white border border-slate-200 text-slate-800 rounded-2xl p-6 max-w-md shadow-xl">
          <form onSubmit={handleCreateWorkspace}>
            <DialogHeader className="pb-3 border-b border-slate-100">
              <DialogTitle className="text-lg font-bold text-slate-900">Create New Bid Workspace</DialogTitle>
              <DialogDescription className="text-sm text-slate-500 mt-1">
                Workspaces isolate different tender RFP documents, compliance checklists, and proposal drafts.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-750 block">Workspace Name</label>
                <Input
                  value={newWorkspaceName}
                  onChange={e => setNewWorkspaceName(e.target.value)}
                  placeholder="e.g. Govt Cloud Deployment Tender"
                  className="bg-white border-slate-200 focus:border-indigo-500 text-slate-850 text-sm rounded-lg h-10 shadow-sm focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-755 block">Description (Optional)</label>
                <Textarea
                  value={newWorkspaceDesc}
                  onChange={e => setNewWorkspaceDesc(e.target.value)}
                  placeholder="Summarize the bid project details, timeline, or scope..."
                  className="bg-white border-slate-200 focus:border-indigo-500 text-slate-850 text-sm rounded-lg min-h-[90px] shadow-sm resize-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <DialogFooter className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsNewWorkspaceOpen(false)}
                className="rounded-lg h-10 px-5 text-sm font-semibold border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={creatingWorkspace || !newWorkspaceName.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg h-10 px-5 text-sm font-semibold shadow-sm border-0"
              >
                {creatingWorkspace ? 'Creating...' : 'Create Workspace'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
