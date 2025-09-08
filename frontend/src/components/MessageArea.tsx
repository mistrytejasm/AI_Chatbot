import React from 'react';

const PremiumTypingAnimation = () => {
    return (
        <div className="flex items-center">
            <div className="flex items-center space-x-1.5">
                <div className="w-1.5 h-1.5 bg-gray-400/70 rounded-full animate-pulse"
                    style={{ animationDuration: "1s", animationDelay: "0ms" }}></div>
                <div className="w-1.5 h-1.5 bg-gray-400/70 rounded-full animate-pulse"
                    style={{ animationDuration: "1s", animationDelay: "300ms" }}></div>
                <div className="w-1.5 h-1.5 bg-gray-400/70 rounded-full animate-pulse"
                    style={{ animationDuration: "1s", animationDelay: "600ms" }}></div>
            </div>
        </div>
    );
};

const SearchStages = ({ searchInfo }: { searchInfo: any }) => {
    if (!searchInfo || !searchInfo.stages || searchInfo.stages.length === 0) return null;

    return (
        <div className="mb-3 mt-1 relative pl-4">
            <div className="flex flex-col space-y-4 text-sm text-gray-700">
                {searchInfo.stages.includes('searching') && (
                    <div className="relative">
                        <div className="absolute -left-3 top-1 w-2.5 h-2.5 bg-teal-400 rounded-full z-10 shadow-sm"></div>
                        {searchInfo.stages.includes('reading') && (
                            <div className="absolute -left-[7px] top-3 w-0.5 h-[calc(100%+1rem)] bg-gradient-to-b from-teal-300 to-teal-200"></div>
                        )}
                        <div className="flex flex-col">
                            <span className="font-medium mb-2 ml-2">Searching the web</span>
                            <div className="flex flex-wrap gap-2 pl-2 mt-1">
                                <div className="bg-gray-100 text-xs px-3 py-1.5 rounded border border-gray-200 inline-flex items-center">
                                    <svg className="w-3 h-3 mr-1.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                    </svg>
                                    {searchInfo.query}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {searchInfo.stages.includes('reading') && (
                    <div className="relative">
                        <div className="absolute -left-3 top-1 w-2.5 h-2.5 bg-teal-400 rounded-full z-10 shadow-sm"></div>
                        <div className="flex flex-col">
                            <span className="font-medium mb-2 ml-2">Reading sources</span>
                            {searchInfo.urls && searchInfo.urls.length > 0 && (
                                <div className="pl-2 space-y-1">
                                    <div className="flex flex-wrap gap-2">
                                        {Array.isArray(searchInfo.urls) ? (
                                            searchInfo.urls.slice(0, 4).map((url: string, index: number) => {
                                                try {
                                                    const hostname = new URL(url).hostname.replace('www.', '');
                                                    return (
                                                        <div key={index} className="bg-blue-50 text-xs px-3 py-1.5 rounded border border-blue-200 truncate max-w-[250px] transition-all duration-200 hover:bg-blue-100">
                                                            <span className="text-blue-600 font-medium">
                                                                {hostname}
                                                            </span>
                                                        </div>
                                                    );
                                                } catch {
                                                    return (
                                                        <div key={index} className="bg-blue-50 text-xs px-3 py-1.5 rounded border border-blue-200 truncate max-w-[250px]">
                                                            <span className="text-blue-600 font-medium">Source</span>
                                                        </div>
                                                    );
                                                }
                                            })
                                        ) : (
                                            <div className="bg-blue-50 text-xs px-3 py-1.5 rounded border border-blue-200">
                                                Reading source...
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {searchInfo.stages.includes('writing') && (
                    <div className="relative">
                        <div className="absolute -left-3 top-1 w-2.5 h-2.5 bg-teal-400 rounded-full z-10 shadow-sm"></div>
                        <span className="font-medium pl-2">Writing answer</span>
                    </div>
                )}

                {searchInfo.stages.includes('error') && (
                    <div className="relative">
                        <div className="absolute -left-3 top-1 w-2.5 h-2.5 bg-red-400 rounded-full z-10 shadow-sm"></div>
                        <span className="font-medium">Search error</span>
                        <div className="pl-4 text-xs text-red-500 mt-1">
                            {searchInfo.error || "An error occurred during search."}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

// Citation parsing function
const parseCitations = (content: string, citations: string[] = []) => {
    if (!content) return content;

    // Replace citation numbers [1], [2], etc. with clickable elements
    const citationRegex = /\[(\d+)\]/g;
    const parts = content.split(citationRegex);

    const result: (string | JSX.Element)[] = [];

    for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 0) {
            // Regular text
            result.push(parts[i]);
        } else {
            // Citation number
            const citationNum = parseInt(parts[i]);
            const url = citations[citationNum - 1]; // Arrays are 0-indexed

            if (url) {
                result.push(
                    <button
                        key={`citation-${i}`}
                        onClick={() => window.open(url, '_blank')}
                        className="inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-full hover:bg-blue-100 hover:border-blue-300 transition-colors duration-200 mx-0.5 cursor-pointer"
                        title={`Source: ${new URL(url).hostname}`}
                    >
                        {citationNum}
                    </button>
                );
            } else {
                result.push(`[${citationNum}]`);
            }
        }
    }

    return result;
};

// Enhanced markdown parser with citation support
const parseMarkdown = (content: string, citations: string[] = []) => {
    if (!content) return content;

    // Clean up the content first
    let cleanContent = content
        // Remove excessive dashes (table separators)
        .replace(/^\|[-\s:]+\|$/gm, '')
        // Remove standalone dash lines
        .replace(/^[-\s]+$/gm, '')
        // Clean up multiple empty lines
        .replace(/\n\s*\n\s*\n/g, '\n\n')
        .trim();

    const lines = cleanContent.split('\n');
    const parsed: JSX.Element[] = [];
    let listItems: string[] = [];
    let inList = false;
    let tableRows: string[][] = [];
    let inTable = false;
    let tableHeaders: string[] = [];

    const flushList = () => {
        if (listItems.length > 0) {
            parsed.push(
                <ul key={`list-${parsed.length}`} className="list-none space-y-1.5 mb-3 ml-0">
                    {listItems.map((item, idx) => (
                        <li key={idx} className="flex items-start">
                            <span className="text-teal-500 mr-3 mt-0.5 flex-shrink-0 text-sm">•</span>
                            <span className="text-gray-700 leading-relaxed text-sm">{formatInlineMarkdown(item)}</span>
                        </li>
                    ))}
                </ul>
            );
            listItems = [];
        }
        inList = false;
    };

    const flushTable = () => {
        if (tableRows.length > 0) {
            parsed.push(
                <div key={`table-${parsed.length}`} className="overflow-x-auto mb-4">
                    <table className="min-w-full border border-gray-200 rounded-lg shadow-sm">
                        {tableHeaders.length > 0 && (
                            <thead className="bg-gray-50">
                                <tr>
                                    {tableHeaders.map((header, idx) => (
                                        <th key={idx} className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">
                                            {formatInlineMarkdown(header.trim())}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                        )}
                        <tbody className="bg-white divide-y divide-gray-200">
                            {tableRows.map((row, rowIdx) => (
                                <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                    {row.map((cell, cellIdx) => (
                                        <td key={cellIdx} className="px-4 py-3 text-sm text-gray-700 border-b border-gray-100">
                                            {formatInlineMarkdown(cell.trim())}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
            tableRows = [];
            tableHeaders = [];
        }
        inTable = false;
    };

    // Updated formatInlineMarkdown with citation support
    const formatInlineMarkdown = (text: string): JSX.Element => {
        // Handle bold text
        let parts = text.split(/(\*\*.*?\*\*)/g);
        const formatted = parts.map((part, idx) => {
            if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
                return <strong key={idx} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>;
            }
            // Handle italic text
            if (part.startsWith('*') && part.endsWith('*') && part.length > 2 && !part.startsWith('**')) {
                return <em key={idx} className="italic">{part.slice(1, -1)}</em>;
            }
            return part;
        });

        // Process citations in the formatted text
        return (
            <span>
                {formatted.map((formattedPart, idx) => {
                    if (typeof formattedPart === 'string') {
                        return parseCitations(formattedPart, citations);
                    }
                    return formattedPart;
                })}
            </span>
        );
    };

    lines.forEach((line, index) => {
        const trimmed = line.trim();

        // Skip empty lines or lines with just dashes
        if (!trimmed || /^[-\s|:]+$/.test(trimmed)) {
            return;
        }

        // Detect table rows
        if (trimmed.includes('|') && trimmed.split('|').length > 2) {
            const cells = trimmed.split('|').map(cell => cell.trim()).filter(cell => cell.length > 0);

            if (cells.length > 0) {
                if (!inTable) {
                    flushList();
                    inTable = true;
                    // First row becomes header
                    tableHeaders = cells;
                } else {
                    // Subsequent rows are data
                    tableRows.push(cells);
                }
                return;
            }
        } else {
            // Not a table line, flush any pending table
            flushTable();
        }

        // Headers
        if (trimmed.startsWith('## ')) {
            flushList();
            flushTable();
            parsed.push(
                <h2 key={`h2-${index}`} className="text-lg font-semibold text-gray-800 mb-2 mt-4 first:mt-0 pb-1 border-b border-gray-200">
                    {formatInlineMarkdown(trimmed.slice(3))}
                </h2>
            );
        } else if (trimmed.startsWith('### ')) {
            flushList();
            flushTable();
            parsed.push(
                <h3 key={`h3-${index}`} className="text-base font-medium text-gray-800 mb-2 mt-3 first:mt-0">
                    {formatInlineMarkdown(trimmed.slice(4))}
                </h3>
            );
        } else if (trimmed.startsWith('#### ')) {
            flushList();
            flushTable();
            parsed.push(
                <h4 key={`h4-${index}`} className="text-sm font-medium text-gray-800 mb-1 mt-2 first:mt-0">
                    {formatInlineMarkdown(trimmed.slice(5))}
                </h4>
            );
        }
        // List items
        else if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || /^\d+\.\s/.test(trimmed)) {
            flushTable();
            inList = true;
            const itemText = trimmed.replace(/^[•\-]\s/, '').replace(/^\d+\.\s/, '');
            listItems.push(itemText);
        }
        // Regular paragraphs
        else if (trimmed.length > 0) {
            flushList();
            flushTable();
            parsed.push(
                <p key={`p-${index}`} className="text-gray-700 mb-2 leading-relaxed text-sm">
                    {formatInlineMarkdown(trimmed)}
                </p>
            );
        }
    });

    // Flush any remaining items
    flushList();
    flushTable();

    return <div className="space-y-1">{parsed}</div>;
};

// Updated Message interface with citations
interface Message {
    id: number;
    content: string;
    isUser: boolean;
    type: string;
    isLoading?: boolean;
    searchInfo?: any;
    citations?: string[]; // Added this line
}

interface MessageAreaProps {
    messages: Message[];
}

// MessageArea component
const MessageArea: React.FC<MessageAreaProps> = ({ messages }) => {
    return (
        <div className="flex-grow overflow-y-auto bg-[#FCFCF8] border-b border-gray-100" style={{ minHeight: 0 }}>
            <div className="max-w-6xl mx-auto p-4">
                {messages.map((message) => (
                    <div key={message.id} className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} mb-4`}>
                        <div className={`flex flex-col ${message.isUser ? 'max-w-md' : 'max-w-5xl w-full'}`}>
                            {/* Search Status Display */}
                            {!message.isUser && message.searchInfo && (
                                <SearchStages searchInfo={message.searchInfo} />
                            )}

                            {/* Message Content */}
                            <div
                                className={`rounded-lg py-3 px-4 ${message.isUser
                                    ? 'bg-gradient-to-br from-[#5E507F] to-[#4A3F71] text-white rounded-br-none shadow-md'
                                    : 'bg-white text-gray-800 border border-gray-200 rounded-bl-none shadow-sm'
                                }`}
                            >
                                {message.isLoading ? (
                                    <PremiumTypingAnimation />
                                ) : (
                                    <div className="max-w-none">
                                        {message.isUser ? (
                                            <p className="mb-0 text-white text-sm">{message.content}</p>
                                        ) : (
                                            parseMarkdown(message.content || "Waiting for response...", message.citations || [])
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Citations List (Optional - for reference) */}
                            {!message.isUser && message.citations && message.citations.length > 0 && (
                                <div className="mt-2 text-xs text-gray-500">
                                    <details className="cursor-pointer">
                                        <summary className="hover:text-gray-700">Sources ({message.citations.length})</summary>
                                        <div className="mt-1 space-y-1 pl-4">
                                            {message.citations.map((url, idx) => (
                                                <div key={idx} className="flex items-start">
                                                    <span className="font-mono text-blue-600 mr-2">[{idx + 1}]</span>
                                                    <a
                                                        href={url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 hover:text-blue-800 underline truncate max-w-xs"
                                                    >
                                                        {new URL(url).hostname}
                                                    </a>
                                                </div>
                                            ))}
                                        </div>
                                    </details>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default MessageArea;
