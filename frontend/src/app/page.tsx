"use client"

import Header from '@/components/Header';
import InputBar from '@/components/InputBar';
import MessageArea from '@/components/MessageArea';
import React, { useState } from 'react';

interface SearchInfo {
  stages: string[];
  query: string;
  urls: string[];
}

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  type: string;
  isLoading?: boolean;
  searchInfo?: SearchInfo;
}

const Home = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      content: 'Hi there, how can I help you?',
      isUser: false,
      type: 'message'
    }
  ]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [checkpointId, setCheckpointId] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (currentMessage.trim()) {
      // First add the user message to the chat
      const newMessageId = messages.length > 0 ? Math.max(...messages.map(msg => msg.id)) + 1 : 1;

      setMessages(prev => [
        ...prev,
        {
          id: newMessageId,
          content: currentMessage,
          isUser: true,
          type: 'message'
        }
      ]);

      const userInput = currentMessage;
      setCurrentMessage(""); // Clear input field immediately

      try {
        // Create AI response placeholder
        const aiResponseId = newMessageId + 1;
        setMessages(prev => [
          ...prev,
          {
            id: aiResponseId,
            content: "",
            isUser: false,
            type: 'message',
            isLoading: true,
            searchInfo: {
              stages: [],
              query: "",
              source: "",
              subQueries: [],
              urls: [],
              sources: [],
              webSources: [],
              documentSources: []
            }
          }
        ]);

        // Create URL with checkpoint ID if it exists
        let url = `http://localhost:8000/chat_stream?message=${encodeURIComponent(userInput)}`;
        if (checkpointId) url += `&checkpoint_id=${encodeURIComponent(checkpointId)}`;

        // Connect to SSE endpoint using EventSource
        const eventSource = new EventSource(url);
        let streamedContent = "";
        let searchData = null;
        let hasReceivedContent = false;

        // Process incoming messages
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'checkpoint') {
              // Store the checkpoint ID for future requests
              setCheckpointId(data.checkpoint_id);
            }
            else if (data.type === 'content') {
              streamedContent += data.content;
              hasReceivedContent = true;

              // Update message with accumulated content
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === aiResponseId
                    ? { ...msg, content: streamedContent, isLoading: false }
                    : msg
                )
              );
            }
            else if (data.type === 'search_start') {
              // Handle search start with original query
              const newSearchInfo = {
                stages: ['searching'],
                query: data.query,
                source: data.source || 'controlled',
                subQueries: [],
                urls: [],
                sources: [],
                webSources: [],
                documentSources: []
              };
              searchData = newSearchInfo;

              setMessages(prev =>
                prev.map(msg =>
                  msg.id === aiResponseId
                    ? { ...msg, content: streamedContent, searchInfo: newSearchInfo, isLoading: false }
                    : msg
                )
              );
            }
            else if (data.type === 'query_breakdown') {
              // Handle original + sub-queries display
              const newSearchInfo = {
                stages: ['searching'],
                query: data.original_query,
                source: 'controlled',
                subQueries: data.sub_queries || [],
                urls: [],
                sources: [],
                webSources: [],
                documentSources: []
              };
              searchData = newSearchInfo;

              setMessages(prev =>
                prev.map(msg =>
                  msg.id === aiResponseId
                    ? { ...msg, content: streamedContent, searchInfo: newSearchInfo, isLoading: false }
                    : msg
                )
              );

              console.log('📋 Query breakdown received:', {
                original: data.original_query,
                subQueries: data.sub_queries?.length || 0
              });
            }
            else if (data.type === 'search_results') {
              try {
                console.log('🔍 Raw search_results data:', data); // DEBUG LINE
                let newSearchInfo;
                
                if (data.source === 'controlled') {
                  // Handle enhanced controlled search results
                  const webSources = data.web_sources || [];
                  const docSources = data.document_sources || [];

                  console.log('📊 Enhanced source processing:', { 
                    webCount: webSources.length,
                    docCount: docSources.length,
                    webSources: webSources.slice(0, 3), // Show first 3 for debugging
                    docSources: docSources.slice(0, 3)  // Show first 3 for debugging
                  });

                  
                  newSearchInfo = {
                    stages: searchData ? [...searchData.stages, 'reading'] : ['reading'],
                    query: searchData?.query || "",
                    source: 'controlled',
                    subQueries: searchData?.subQueries || [],
                    webSources: webSources,
                    documentSources: docSources,
                    urls: webSources.map(s => s?.url).filter(Boolean),
                    sources: docSources.map(s => s?.filename).filter(Boolean)
                  };
                  
                  console.log('🔍 Enhanced search results:', {
                    web: webSources.length,
                    docs: docSources.length,
                    totalSources: webSources.length + docSources.length
                  });
                  console.log('✅ Final searchInfo:', newSearchInfo); // DEBUG LINE
                } else {
                  // Handle traditional web search results
                  const urls = typeof data.urls === 'string' ? JSON.parse(data.urls) : (data.urls || []);
                  newSearchInfo = {
                    stages: searchData ? [...searchData.stages, 'reading'] : ['reading'],
                    query: searchData?.query || "",
                    source: data.source || 'web',
                    subQueries: searchData?.subQueries || [],
                    urls: urls,
                    sources: searchData?.sources || [],
                    webSources: urls.map(url => ({ url, domain: url.split('//')[1]?.split('/')[0] || 'unknown' })),
                    documentSources: searchData?.documentSources || []
                  };
                  
                  console.log('🌐 Web search results:', urls.length);
                }
                
                searchData = newSearchInfo;

                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === aiResponseId
                      ? { ...msg, content: streamedContent, searchInfo: newSearchInfo, isLoading: false }
                      : msg
                  )
                );
              } catch (parseError) {
                console.error("Error parsing search results:", parseError);
                
                // Fallback handling
                const fallbackSearchInfo = {
                  stages: searchData ? [...searchData.stages, 'reading'] : ['reading'],
                  query: searchData?.query || "",
                  source: data.source || 'controlled',
                  subQueries: searchData?.subQueries || [],
                  urls: searchData?.urls || [],
                  sources: searchData?.sources || [],
                  webSources: searchData?.webSources || [],
                  documentSources: searchData?.documentSources || [],
                  error: "Failed to parse search results"
                };
                
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === aiResponseId
                      ? { ...msg, content: streamedContent, searchInfo: fallbackSearchInfo, isLoading: false }
                      : msg
                  )
                );
              }
            }
            else if (data.type === 'search_error') {
              // Handle search error for both web and document search
              const newSearchInfo = {
                stages: searchData ? [...searchData.stages, 'error'] : ['error'],
                query: searchData?.query || "",
                source: searchData?.source || data.source || 'controlled',
                subQueries: searchData?.subQueries || [],
                error: data.error,
                urls: searchData?.urls || [],
                sources: searchData?.sources || [],
                webSources: searchData?.webSources || [],
                documentSources: searchData?.documentSources || []
              };
              searchData = newSearchInfo;

              setMessages(prev =>
                prev.map(msg =>
                  msg.id === aiResponseId
                    ? { ...msg, content: streamedContent, searchInfo: newSearchInfo, isLoading: false }
                    : msg
                )
              );
            }
            else if (data.type === 'end') {
              // When stream ends, add 'writing' stage if we had search info
              if (searchData) {
                const finalSearchInfo = {
                  ...searchData,
                  stages: [...searchData.stages, 'writing']
                };

                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === aiResponseId
                      ? { ...msg, searchInfo: finalSearchInfo, isLoading: false }
                      : msg
                  )
                );
                }

              eventSource.close();
            }
          } catch (error) {
            console.error("Error parsing event data:", error, event.data);
            
            // Add error handling for malformed data
            setMessages(prev =>
              prev.map(msg =>
                msg.id === aiResponseId
                  ? { 
                      ...msg, 
                      content: streamedContent || "Error processing response", 
                      isLoading: false,
                      searchInfo: {
                        ...msg.searchInfo,
                        stages: [...(msg.searchInfo?.stages || []), 'error'],
                        error: "Failed to parse server response"
                      }
                    }
                  : msg
              )
            );
          }
        };

        // Handle errors
        eventSource.onerror = (error) => {
          console.error("EventSource error:", error);
          eventSource.close();

          // Only update with error if we don't have content yet
          if (!streamedContent) {
            setMessages(prev =>
              prev.map(msg =>
                msg.id === aiResponseId
                  ? { 
                      ...msg, 
                      content: "Sorry, there was an error processing your request.", 
                      isLoading: false,
                      searchInfo: {
                        ...msg.searchInfo,
                        stages: ['error'],
                        error: "Connection error"
                      }
                    }
                  : msg
              )
            );
          }
        };

        // Listen for end event
        eventSource.addEventListener('end', () => {
          eventSource.close();
        });

      } catch (error) {
        console.error("Error setting up EventSource:", error);
        setMessages(prev => [
          ...prev,
          {
            id: newMessageId + 1,
            content: "Sorry, there was an error connecting to the server.",
            isUser: false,
            type: 'message',
            isLoading: false,
            searchInfo: {
              stages: ['error'],
              error: "Connection failed"
            }
          }
        ]);
      }
    }
  };

  return (
    <div className="flex justify-center bg-gray-100 min-h-screen py-8 px-4">
      {/* Main container with refined shadow and border */}
      <div className="w-[60%] bg-white flex flex-col rounded-xl shadow-lg border border-gray-100 overflow-hidden h-[90vh]">
        <Header />
        <MessageArea messages={messages} />
        <InputBar currentMessage={currentMessage} setCurrentMessage={setCurrentMessage} onSubmit={handleSubmit} />
      </div>
    </div>
  );
};

export default Home;