/**
 * Node Configuration Modal Component
 *
 * Provides a modal dialog for configuring workflow nodes with:
 * - Label editing
 * - Node type-specific configuration fields
 * - Form validation
 * - Save/Cancel actions
 */

import { useState, useEffect, useCallback } from 'react';
import { X, Settings } from 'lucide-react';
import type { Node } from 'reactflow';

// ==============================================================================
// Types
// ==============================================================================

interface NodeData {
  label: string;
  nodeType: 'tool' | 'llm' | 'conditional' | 'approval' | 'custom';
  config: Record<string, any>;
}

interface WorkflowNode extends Node {
  data: NodeData;
}

interface NodeConfigModalProps {
  isOpen: boolean;
  node: WorkflowNode | null;
  onSave: (node: WorkflowNode) => void;
  onClose: () => void;
}

interface FormErrors {
  label?: string;
  [key: string]: string | undefined;
}

// ==============================================================================
// Node Type Configurations
// ==============================================================================

const nodeTypeConfigs: Record<string, { label: string; fields: FieldConfig[] }> = {
  tool: {
    label: 'Tool Node',
    fields: [
      { name: 'toolName', label: 'Tool Name', type: 'text', placeholder: 'e.g., search_web' },
      { name: 'timeout', label: 'Timeout (seconds)', type: 'number', default: 30 },
    ],
  },
  llm: {
    label: 'LLM Node',
    fields: [
      {
        name: 'model',
        label: 'Model',
        type: 'select',
        options: ['gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'claude-3-sonnet'],
      },
      { name: 'temperature', label: 'Temperature', type: 'number', min: 0, max: 2, step: 0.1, default: 0.7 },
      { name: 'systemPrompt', label: 'System Prompt', type: 'textarea', placeholder: 'Enter system prompt...' },
    ],
  },
  conditional: {
    label: 'Conditional Node',
    fields: [
      { name: 'condition', label: 'Condition Expression', type: 'textarea', placeholder: 'e.g., state.value > 0' },
    ],
  },
  approval: {
    label: 'Approval Node',
    fields: [
      { name: 'approverRole', label: 'Approver Role', type: 'text', placeholder: 'e.g., admin' },
      { name: 'timeoutMinutes', label: 'Timeout (minutes)', type: 'number', default: 60 },
    ],
  },
  custom: {
    label: 'Custom Node',
    fields: [
      { name: 'functionName', label: 'Function Name', type: 'text', placeholder: 'e.g., process_data' },
      { name: 'code', label: 'Python Code', type: 'textarea', placeholder: 'def process(state):\n    return state' },
    ],
  },
};

interface FieldConfig {
  name: string;
  label: string;
  type: 'text' | 'number' | 'textarea' | 'select';
  placeholder?: string;
  default?: any;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
}

// ==============================================================================
// Component Implementation
// ==============================================================================

export function NodeConfigModal({ isOpen, node, onSave, onClose }: NodeConfigModalProps) {
  const [label, setLabel] = useState('');
  const [config, setConfig] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<FormErrors>({});

  // Reset form when node changes
  useEffect(() => {
    if (node) {
      setLabel(node.data.label);
      setConfig(node.data.config || {});
      setErrors({});
    }
  }, [node]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Validate form
  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!label.trim()) {
      newErrors.label = 'Label is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [label]);

  // Check if form has errors
  const hasErrors = !label.trim();

  // Handle save
  const handleSave = useCallback(() => {
    if (!node) return;

    if (!validate()) {
      return;
    }

    const updatedNode: WorkflowNode = {
      ...node,
      data: {
        ...node.data,
        label,
        config,
      },
    };

    onSave(updatedNode);
    onClose();
  }, [node, label, config, validate, onSave, onClose]);

  // Handle config field change
  const handleConfigChange = useCallback((fieldName: string, value: any) => {
    setConfig((prev) => ({ ...prev, [fieldName]: value }));
  }, []);

  // Don't render if not open
  if (!isOpen || !node) {
    return null;
  }

  const nodeTypeConfig = nodeTypeConfigs[node.data.nodeType] || nodeTypeConfigs.custom;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        data-testid="modal-backdrop"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Settings size={20} className="text-gray-600" />
            <h2 id="modal-title" className="text-lg font-semibold">
              Configure: {node.data.label}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4">
          {/* Node Type Badge */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Type:</span>
            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded capitalize">
              {node.data.nodeType}
            </span>
          </div>

          {/* Label Field */}
          <div>
            <label htmlFor="node-label" className="block text-sm font-medium text-gray-700 mb-1">
              Label
            </label>
            <input
              id="node-label"
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.label ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="Node label"
            />
            {errors.label && (
              <p className="mt-1 text-sm text-red-600">{errors.label}</p>
            )}
          </div>

          {/* Node Type Specific Fields */}
          {nodeTypeConfig.fields.map((field) => (
            <div key={field.name}>
              <label
                htmlFor={`config-${field.name}`}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {field.label}
              </label>

              {field.type === 'text' && (
                <input
                  id={`config-${field.name}`}
                  type="text"
                  value={config[field.name] || ''}
                  onChange={(e) => handleConfigChange(field.name, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={field.placeholder}
                />
              )}

              {field.type === 'number' && (
                <input
                  id={`config-${field.name}`}
                  type="number"
                  value={config[field.name] ?? field.default ?? ''}
                  onChange={(e) => handleConfigChange(field.name, parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min={field.min}
                  max={field.max}
                  step={field.step}
                />
              )}

              {field.type === 'textarea' && (
                <textarea
                  id={`config-${field.name}`}
                  value={config[field.name] || ''}
                  onChange={(e) => handleConfigChange(field.name, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px]"
                  placeholder={field.placeholder}
                />
              )}

              {field.type === 'select' && (
                <select
                  id={`config-${field.name}`}
                  value={config[field.name] || ''}
                  onChange={(e) => handleConfigChange(field.name, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select {field.label}</option>
                  {field.options?.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={hasErrors}
            className={`px-4 py-2 text-white bg-blue-600 rounded-md ${
              hasErrors ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'
            }`}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default NodeConfigModal;
