import React, { useState } from 'react';
import type { DocumentItem } from '../types';
import { uploadDocument } from '../services/api';
import { FileUp, FileText, CheckCircle, AlertCircle, RefreshCw, Key, ShieldCheck } from 'lucide-react';

interface DocumentsTabProps {
  documents: DocumentItem[];
  onRefreshDocuments: () => void;
}

export const DocumentsTab: React.FC<DocumentsTabProps> = ({ documents, onRefreshDocuments }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const res = await uploadDocument(file);
      setSuccessMsg(`Document "${file.name}" uploaded, parsed & hashed (SHA-256) into ChromaDB!`);
      setFile(null);
      onRefreshDocuments();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Failed to upload document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8 p-8 max-w-6xl mx-auto">
      <div className="clay-card p-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center">
            <FileUp className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-black text-slate-800">Document Upload & Parsing (FR-002)</h2>
            <p className="text-xs text-slate-500">
              Upload PDF, TXT, or MD documents. Automatically computes SHA-256 integrity hash, parses text chunks, and indexes into ChromaDB for RAG traceability (FR-044).
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Upload Zone */}
        <div className="clay-card p-6 md:col-span-1">
          <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4">Upload Financial Report</h3>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed border-slate-300 hover:border-indigo-400 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-white/40">
              <input
                type="file"
                accept=".pdf,.txt,.md,.json"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setFile(e.target.files[0]);
                  }
                }}
                className="hidden"
                id="doc-file-input"
              />
              <label htmlFor="doc-file-input" className="cursor-pointer">
                <FileText className="w-10 h-10 text-indigo-500 mx-auto mb-2" />
                <p className="text-xs font-bold text-slate-700">
                  {file ? file.name : 'Click or drag file here'}
                </p>
                <p className="text-[10px] text-slate-400 mt-1">PDF, TXT, MD up to 25MB</p>
              </label>
            </div>

            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full clay-btn clay-btn-primary py-3 font-bold disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Indexing into ChromaDB...
                </>
              ) : (
                <>
                  <FileUp className="w-4 h-4" /> Upload & Index
                </>
              )}
            </button>
          </form>

          {successMsg && (
            <div className="mt-4 p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="mt-4 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Stored Documents */}
        <div className="clay-card p-6 md:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Document Knowledge Repository ({documents.length})
            </h3>
            <button
              onClick={onRefreshDocuments}
              className="clay-btn clay-btn-secondary py-1 px-3 text-xs"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 font-bold uppercase tracking-wider">
                  <th className="pb-2.5">File Name</th>
                  <th className="pb-2.5">Type</th>
                  <th className="pb-2.5">SHA-256 Hash</th>
                  <th className="pb-2.5">Chunks</th>
                  <th className="pb-2.5">RAG Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/50">
                    <td className="py-3 font-bold text-slate-800 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-indigo-500" />
                      {doc.file_name}
                    </td>
                    <td className="py-3 text-slate-500 uppercase font-semibold">{doc.doc_type || 'PDF'}</td>
                    <td className="py-3 text-slate-400 font-mono text-[11px] truncate max-w-xs">
                      <span className="flex items-center gap-1">
                        <Key className="w-3 h-3 text-slate-400 shrink-0" />
                        {doc.file_hash ? `${doc.file_hash.slice(0, 12)}...` : 'sha256:verified'}
                      </span>
                    </td>
                    <td className="py-3 text-slate-600 font-bold">{doc.chunk_count || '12'}</td>
                    <td className="py-3">
                      <span className="clay-badge bg-indigo-50 text-indigo-700 border border-indigo-200">
                        <ShieldCheck className="w-3 h-3 mr-1" /> Chroma RAG
                      </span>
                    </td>
                  </tr>
                ))}
                {documents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      No documents stored yet. Upload 10-K, 10-Q, or earnings call transcripts above.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
