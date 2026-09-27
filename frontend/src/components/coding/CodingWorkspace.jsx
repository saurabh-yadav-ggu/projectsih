import React, { useState } from 'react';
import { useCodingState } from '../../hooks/useCodingState';
import CodingHeader from './CodingHeader';
import FileExplorer from './FileExplorer';
import MonacoEditorArea from './MonacoEditorArea';
import TerminalDrawer from './TerminalDrawer';
import CodingAgentPanel from './CodingAgentPanel';
import WorkspaceModal from './WorkspaceModal';

export default function CodingWorkspace({
  token,
  user,
  activeTab = 'Coding',
  setActiveTab,
}) {
  const {
    workspaceTree,
    workspaceRoot,
    gitStatus,
    openTabs,
    activeTabPath,
    isLoadingFile,
    isTreeLoading,
    terminalLines,
    terminalCwd,
    isTerminalRunning,
    agentMessages,
    agentStatus,
    currentTool,
    approvalRequest,
    hitlMode,
    setHitlMode,
    selectedModel,
    setSelectedModel,
    isConnected,
    availableWorkspaces,
    isSwitchingWorkspace,
    switchWorkspace,
    openFile,
    closeTab,
    updateTabContent,
    saveActiveFile,
    createFile,
    deleteFile,
    renameFile,
    refreshTree,
    runTerminalCommand,
    sendAgentPrompt,
    respondApproval,
    stopAgent,
    resetAgent,
    sessionId,
    sessions,
    createNewConversation,
    switchSession,
    deleteSession,
  } = useCodingState({ token, user });

  const [isWorkspaceModalOpen, setIsWorkspaceModalOpen] = useState(false);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        backgroundColor: '#000000',
        overflow: 'hidden',
      }}
    >
      {/* 1. Top IDE Header */}
      <CodingHeader
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        workspaceRoot={workspaceRoot}
        isConnected={isConnected}
        selectedModel={selectedModel}
        onChangeModel={setSelectedModel}
        hitlMode={hitlMode}
        onChangeHitlMode={setHitlMode}
        user={user}
        onOpenWorkspaceModal={() => setIsWorkspaceModalOpen(true)}
      />

      {/* 2. Main 3-Column IDE Body */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          overflow: 'hidden',
          width: '100%',
        }}
      >
        {/* Left Column: File Explorer */}
        <FileExplorer
          tree={workspaceTree}
          workspaceRoot={workspaceRoot}
          activePath={activeTabPath}
          onSelectFile={openFile}
          onCreateFile={createFile}
          onDeleteFile={deleteFile}
          onRefresh={refreshTree}
          isLoading={isTreeLoading}
          onOpenWorkspaceModal={() => setIsWorkspaceModalOpen(true)}
          onSelectWorkspace={switchWorkspace}
        />

        {/* Center Column: Monaco Editor + Terminal Drawer */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            minWidth: '400px',
          }}
        >
          <MonacoEditorArea
            tabs={openTabs}
            activeTabPath={activeTabPath}
            onSelectTab={openFile}
            onCloseTab={closeTab}
            onChangeContent={updateTabContent}
            onSaveFile={saveActiveFile}
            isLoading={isLoadingFile}
          />

          <TerminalDrawer
            lines={terminalLines}
            cwd={terminalCwd}
            isRunning={isTerminalRunning}
            onRunCommand={runTerminalCommand}
            gitStatus={gitStatus}
          />
        </div>

        {/* Right Column: AI Coding Agent Panel */}
        <CodingAgentPanel
          sessionId={sessionId}
          sessions={sessions}
          messages={agentMessages}
          status={agentStatus}
          currentTool={currentTool}
          approvalRequest={approvalRequest}
          selectedModel={selectedModel}
          onChangeModel={setSelectedModel}
          onSendMessage={sendAgentPrompt}
          onStop={stopAgent}
          onReset={resetAgent}
          onNewConversation={createNewConversation}
          onSwitchSession={switchSession}
          onDeleteSession={deleteSession}
          onRespondApproval={respondApproval}
        />
      </div>

      {/* Workspace Directory Selector Modal */}
      <WorkspaceModal
        isOpen={isWorkspaceModalOpen}
        onClose={() => setIsWorkspaceModalOpen(false)}
        token={token}
        currentWorkspace={workspaceRoot}
        suggestedWorkspaces={availableWorkspaces}
        onSelectWorkspace={switchWorkspace}
        isSwitching={isSwitchingWorkspace}
      />
    </div>
  );
}
