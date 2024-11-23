'use client'
import React, { useCallback, useState } from 'react';
import axios,{AxiosError} from 'axios';
import { FileImage, UploadCloud, X, Download, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { BACKEND_URL } from '@/lib/config';

interface FileUploadProgress {
  progress: number;
  File: File;
  status: 'queued' | 'uploading' | 'processing' | 'completed' | 'failed';
  convertedUrl?: string;
  error?: string;
}

const ImageColor = {
  fillColor: 'fill-purple-600',
};

const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="text-green-500" size={20} />;
    case 'failed':
      return <AlertCircle className="text-red-500" size={20} />;
    case 'processing':
    case 'queued':
      return <Clock className="text-yellow-500" size={20} />;
    default:
      return null;
  }
};

const StatusBadge = ({ status }: { status: FileUploadProgress['status'] }) => {
  const styles = {
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    processing: 'bg-yellow-100 text-yellow-800',
    queued: 'bg-blue-100 text-blue-800',
    uploading: 'bg-purple-100 text-purple-800'
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export default function ImageUpload() {
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadProgress[]>([]);
  const [filesToUpload, setFilesToUpload] = useState<FileUploadProgress[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedFormat, setSelectedFormat] = useState('jpeg');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      progress: 0,
      File: file,
      status: 'queued' as const
    }));
    setFilesToUpload((prevFiles) => [...prevFiles, ...newFiles]);
  }, []);

  const removeFile = (fileToRemove: File) => {
    setUploadedFiles((prevFiles) => prevFiles.filter((file) => file.File !== fileToRemove));
    setFilesToUpload((prevFiles) => prevFiles.filter((file) => file.File !== fileToRemove));
  };

  const handleFormatChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedFormat(event.target.value);
  };

  const handleDownload = async (file: FileUploadProgress) => {
    if (file.convertedUrl) {
      try {
        const response = await axios.get(`${BACKEND_URL}${file.convertedUrl}`, { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `converted-${file.File.name.slice(0, file.File.name.lastIndexOf('.'))}.${selectedFormat}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } catch {
        setError('Failed to download converted file');
      }
    }
  };

  const pollJobStatus = async (jobId: string, file: FileUploadProgress) => {
    const updateFileStatus = (status: FileUploadProgress['status'], convertedUrl?: string, error?: string) => {
      setUploadedFiles(prev => 
        prev.map(f => 
          f.File === file.File 
            ? { ...f, status, convertedUrl, error }
            : f
        )
      );
    };

    try {
      const response = await axios.get(`${BACKEND_URL}/api/status/${jobId}`);
      const { status, output_path, error } = response.data;

      if (status === 'completed') {
        updateFileStatus('completed', output_path);
      } else if (status === 'failed') {
        updateFileStatus('failed', undefined, error);
      } else {
        updateFileStatus('processing');
        setTimeout(() => pollJobStatus(jobId, file), 2000);
      }
    } catch {
      updateFileStatus('failed', undefined, 'Failed to check conversion status');
    }
  };

  const handleSubmit = async () => {
    setError(null);
    const formData = new FormData();
    filesToUpload.forEach(file => formData.append('files', file.File));
    formData.append("output_format", selectedFormat);

    try {
      setFilesToUpload(prev => prev.map(file => ({ ...file, status: 'uploading' })));

      const response = await axios.post(`${BACKEND_URL}/api/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = progressEvent.total ? Math.round((progressEvent.loaded * 100) / progressEvent.total) : 0;
          setFilesToUpload(prevFiles => prevFiles.map(file => ({ ...file, progress: percentCompleted })));
        }
      });

      if (response.data.success) {
        const newUploadedFiles = filesToUpload.map(file => ({ ...file, status: 'processing' as const }));
        setUploadedFiles(prev => [...prev, ...newUploadedFiles]);
        setFilesToUpload([]);

        response.data.jobs.forEach((job: { job_id: string }, index: number) => {
          pollJobStatus(job.job_id, newUploadedFiles[index]);
        });
      }
    } catch(error) {
      const errorMessage = error instanceof AxiosError 
        ? error.response?.data?.detail || error.response?.data?.message || error.message
        : 'An unexpected error occurred';
      
      setError(errorMessage);
      setFilesToUpload(prev => prev.map(file => ({ ...file, progress: 0, status: 'failed' })));
    }
  };

  const { getRootProps, getInputProps } = useDropzone({ onDrop });

  return (
    <div className="max-w-3xl mx-auto p-6">
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mb-6">
        <label
          {...getRootProps()}
          className="relative flex flex-col items-center justify-center w-full py-6 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <div className="text-center">
            <div className="border p-2 rounded-md max-w-min mx-auto">
              <UploadCloud size={20} />
            </div>
            <p className="mt-2 text-sm text-gray-600">
              <span className="font-semibold">Drag files</span>
            </p>
            <p className="text-xs text-gray-500">
              Click to upload files (files should be under 10 MB)
            </p>
          </div>
        </label>

        <Input
          {...getInputProps()}
          id="dropzone-file"
          accept="image/png, image/jpeg"
          type="file"
          className="hidden"
        />
      </div>

      {filesToUpload.length > 0 && (
        <div className="mb-6">
          <ScrollArea className="h-100">
            <p className="font-medium my-2 text-muted-foreground text-sm">
              Files to Upload
            </p>
            <div className="space-y-2 pr-3">
              {filesToUpload.map((file, ind) => (
                <div
                  key={ind}
                  className="flex justify-between gap-2 rounded-lg border border-slate-100 group hover:border-slate-300 transition-all"
                >
                  <div className="flex items-center flex-1 p-2">
                    <FileImage size={40} className={ImageColor.fillColor} />
                    <div className="w-full ml-2 space-y-1">
                      <div className="flex justify-between items-center">
                        <p className="text-sm text-muted-foreground">
                          {file.File.name.slice(0, 25)}
                        </p>
                        <StatusBadge status={file.status} />
                      </div>
                      <Progress
                        value={file.progress}
                        className="bg-purple-600"
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(file.File)}
                    className="bg-red-500 text-white px-2 hidden group-hover:flex items-center"
                  >
                    <X size={20} />
                  </button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {uploadedFiles.length > 0 && (
        <div className="mb-6">
          <p className="font-medium my-2 text-muted-foreground text-sm">
            Uploaded Files
          </p>
          <div className="space-y-2 pr-3">
            {uploadedFiles.map((file, ind) => (
              <div
                key={ind}
                className="flex justify-between gap-2 rounded-lg border border-slate-100 group hover:border-slate-300 transition-all"
              >
                <div className="flex items-center flex-1 p-2">
                  <FileImage size={40} className={ImageColor.fillColor} />
                  <div className="w-full ml-2">
                    <div className="flex justify-between items-center">
                      <p className="text-sm text-muted-foreground">
                        {file.File.name.slice(0, 25)}
                      </p>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={file.status} />
                        <StatusIcon status={file.status} />
                        {file.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(file)}
                            className="text-blue-500 hover:text-blue-700"
                          >
                            <Download size={20} />
                          </button>
                        )}
                      </div>
                    </div>
                    {file.error && (
                      <p className="text-xs text-red-500 mt-1">{file.error}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4">
        <label htmlFor="format" className="block text-sm font-medium text-gray-700">
          Select format to convert:
        </label>
        <select
          id="format"
          name="format"
          value={selectedFormat}
          onChange={handleFormatChange}
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
        >
          <option value="jpeg">JPEG</option>
          <option value="png">PNG</option>
          <option value="gif">GIF</option>
          <option value="bmp">BMP</option>
        </select>

        <button
          onClick={handleSubmit}
          disabled={filesToUpload.length === 0}
          className="mt-4 w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          Convert Images
        </button>
      </div>
    </div>
  );
}