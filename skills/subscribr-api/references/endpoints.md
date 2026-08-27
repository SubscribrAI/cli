# Subscribr API Operations

<!-- Generated from openapi/subscribr-v1.json. Do not edit. -->

Subscribr Video public operations use `/api/v1/video/...` as capability slices ship. Intel video lookup/search remains available for YouTube research.

## Channels

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/channels` | `listChannels` | `channels:read` | read |
| `GET` | `/api/v1/channels/{channel}` | `getChannel` | `channels:read` | read |
| `GET` | `/api/v1/channels/{channel}/competitors` | `listChannelCompetitors` | `channels:read` | read |
| `POST` | `/api/v1/channels/{channel}/competitors` | `addChannelCompetitor` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `DELETE` | `/api/v1/channels/{channel}/competitors/{competitor}` | `deleteChannelCompetitor` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |

## Ideas

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/channels/{channel}/ideas` | `listChannelIdeas` | `scripts:read` | read |
| `POST` | `/api/v1/channels/{channel}/ideas` | `createChannelIdea` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/channels/{channel}/ideas/generate` | `generateChannelIdeas` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/channels/{channel}/ideas/generate-from-channel` | `generateIdeasFromChannel` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/channels/{channel}/ideas/generate-from-video` | `generateIdeasFromVideo` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `GET` | `/api/v1/ideas/{idea}` | `getIdea` | `scripts:read` | read |
| `POST` | `/api/v1/ideas/{idea}/change-topic` | `changeIdeaTopic` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/ideas/{idea}/write` | `writeIdea` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |

## Intel

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/intel/bookmarks` | `listIntelBookmarks` | `intel:read` | read |
| `POST` | `/api/v1/intel/bookmarks` | `createIntelBookmark` | `intel:write` | idempotency=unsupported; concurrency=unsupported |
| `DELETE` | `/api/v1/intel/bookmarks/{bookmark}` | `deleteIntelBookmark` | `intel:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/intel/channels/lookup` | `lookupIntelChannel` | `intel:read` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/intel/channels/search` | `searchIntelChannels` | `intel:read` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/intel/videos/lookup` | `lookupIntelVideo` | `intel:read` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/intel/videos/search` | `searchIntelVideos` | `intel:read` | idempotency=unsupported; concurrency=unsupported |

## Operations

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/operations/{operation}` | `getOperation` | `operations:read` | read |

## Projects

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/projects` | `listProjects` | `projects:read` | read |
| `POST` | `/api/v1/projects` | `createProject` | `projects:write` | idempotency=required; concurrency=optional |
| `GET` | `/api/v1/projects/{project}` | `getProject` | `projects:read` | read |
| `PATCH` | `/api/v1/projects/{project}` | `updateProject` | `projects:write` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/projects/{project}/move` | `moveProject` | `projects:write` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/projects/{project}/promote` | `promoteProject` | `projects:write` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/projects/{project}/archive` | `archiveProject` | `projects:write` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/projects/{project}/restore` | `restoreProject` | `projects:write` | idempotency=required; concurrency=required |
| `GET` | `/api/v1/projects/{project}/comments` | `listProjectComments` | `projects:read` | read |
| `POST` | `/api/v1/projects/{project}/comments` | `createProjectComment` | `projects:write` | idempotency=required; concurrency=optional |
| `GET` | `/api/v1/projects/{project}/activity` | `listProjectActivity` | `projects:read` | read |
| `GET` | `/api/v1/projects/{project}/attachments` | `listProjectAttachments` | `projects:read` | read |
| `GET` | `/api/v1/tasks` | `listProjectTasks` | `projects:read` | read |
| `GET` | `/api/v1/project-notifications` | `listProjectNotifications` | `notifications:read` | read |
| `POST` | `/api/v1/project-notifications/{notification}/read` | `readProjectNotification` | `notifications:write` | idempotency=required; concurrency=optional |
| `POST` | `/api/v1/project-notifications/read-all` | `readAllProjectNotifications` | `notifications:write` | idempotency=required; concurrency=optional |
| `GET` | `/api/v1/projects/{project}/production` | `getProjectProduction` | `projects:read` | read |
| `PATCH` | `/api/v1/projects/{project}/production` | `updateProjectProduction` | `projects:write` | idempotency=required; concurrency=required |

## Scripts

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/channels/{channel}/scripts` | `listChannelScripts` | `scripts:read` | read |
| `POST` | `/api/v1/channels/{channel}/scripts` | `createChannelScript` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `GET` | `/api/v1/scripts/{script}` | `getScript` | `scripts:read` | read |
| `POST` | `/api/v1/scripts/{script}/agent/generate` | `startScriptAgentRun` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `GET` | `/api/v1/scripts/{script}/agent/runs/{run}` | `getScriptAgentRun` | `scripts:read` | read |
| `POST` | `/api/v1/scripts/{script}/agent/runs/{run}/cancel` | `cancelScriptAgentRun` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `GET` | `/api/v1/scripts/{script}/content` | `getScriptContent` | `scripts:read` | read |
| `GET` | `/api/v1/scripts/{script}/export` | `exportScript` | `scripts:read` | read |
| `GET` | `/api/v1/scripts/{script}/generate/poll` | `pollScriptGeneration` | `scripts:read` | read |
| `POST` | `/api/v1/scripts/{script}/outline/generate` | `generateScriptOutline` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/scripts/{script}/script/generate` | `generateScript` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/scripts/{script}/script/humanize` | `humanizeScript` | `scripts:write` | idempotency=unsupported; concurrency=unsupported |

## Team

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/team` | `getTeam` |  | read |
| `GET` | `/api/v1/team/credits` | `getTeamCredits` |  | read |
| `GET` | `/api/v1/team/tokens` | `listApiTokens` | `tokens:manage` | read |
| `POST` | `/api/v1/team/tokens` | `createApiToken` | `tokens:manage` | idempotency=unsupported; concurrency=unsupported |
| `DELETE` | `/api/v1/team/tokens/{token}` | `deleteApiToken` | `tokens:manage` | idempotency=unsupported; concurrency=unsupported |

## Templates

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/channels/{channel}/templates` | `listChannelTemplates` | `templates:read` | read |
| `POST` | `/api/v1/channels/{channel}/templates` | `createTemplate` | `templates:write` | idempotency=required; concurrency=unsupported |
| `GET` | `/api/v1/channels/{channel}/templates/{template}` | `getTemplate` | `templates:read` | read |
| `PATCH` | `/api/v1/channels/{channel}/templates/{template}` | `updateTemplate` | `templates:write` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/channels/{channel}/templates/{template}/archive` | `archiveTemplate` | `templates:write` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/channels/{channel}/templates/{template}/restore` | `restoreTemplate` | `templates:write` | idempotency=required; concurrency=required |

## Thumbnails

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/channels/{channel}/thumbnails/generations` | `listThumbnailGenerations` | `scripts:read`, `thumbnails:read` | read |
| `POST` | `/api/v1/channels/{channel}/thumbnails/generations` | `createThumbnailGeneration` | `scripts:write`, `thumbnails:write` | idempotency=unsupported; concurrency=unsupported |
| `GET` | `/api/v1/channels/{channel}/thumbnails/generations/{runId}` | `getThumbnailGeneration` | `scripts:read`, `thumbnails:read` | read |
| `GET` | `/api/v1/team/thumbnails/usage` | `getThumbnailUsage` | `scripts:read`, `thumbnails:read` | read |

## Video

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/video/capabilities` | `videoListCapabilities` | `video:read` | read |
| `GET` | `/api/v1/video/channels` | `videoListChannels` | `video:read` | read |
| `GET` | `/api/v1/video/channels/{videoChannel}` | `videoGetChannel` | `video:read` | read |
| `GET` | `/api/v1/video/voices` | `videoListVoices` | `video:read` | read |
| `GET` | `/api/v1/video/voices/{voice}` | `videoGetVoice` | `video:read` | read |
| `GET` | `/api/v1/video/avatars` | `videoListAvatars` | `video:read` | read |
| `GET` | `/api/v1/video/avatars/{avatar}` | `videoGetAvatar` | `video:read` | read |
| `GET` | `/api/v1/video/media-assets` | `videoListMediaAssets` | `video:read` | read |
| `GET` | `/api/v1/video/media-assets/{mediaAsset}` | `videoGetMediaAsset` | `video:read` | read |
| `GET` | `/api/v1/video/projects` | `videoListProjects` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}` | `videoGetProject` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}/download` | `videoGetProjectDownload` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}/editable-content` | `videoGetEditableContent` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}/revision-manifest` | `videoGetRevisionManifest` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}/overlay-templates` | `videoListOverlayTemplates` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}/quality-report` | `videoGetQualityReport` | `video:read` | read |
| `GET` | `/api/v1/video/projects/{project}/revision/passes/{pass}` | `videoGetRevisionPass` | `video:read` | read |
| `POST` | `/api/v1/video/projects/{project}/revision/overlays` | `videoAddOverlay` | `video:edit` | idempotency=required; concurrency=required |
| `DELETE` | `/api/v1/video/projects/{project}/revision/overlays/{item}` | `videoRemoveStagedOverlay` | `video:edit` | idempotency=required; concurrency=required |
| `PATCH` | `/api/v1/video/projects/{project}/revision/published-overlays/{overlay}` | `videoUpdateOverlay` | `video:edit` | idempotency=required; concurrency=required |
| `DELETE` | `/api/v1/video/projects/{project}/revision/published-overlays/{overlay}` | `videoRemoveOverlay` | `video:edit` | idempotency=required; concurrency=required |
| `PUT` | `/api/v1/video/projects/{project}/revision/captions` | `videoUpdateCaptions` | `video:edit` | idempotency=required; concurrency=required |
| `PUT` | `/api/v1/video/projects/{project}/revision/music` | `videoRemoveMusic` | `video:edit` | idempotency=required; concurrency=required |
| `PATCH` | `/api/v1/video/projects/{project}/revision/slide-text` | `videoEditSlideText` | `video:edit` | idempotency=required; concurrency=required |
| `PUT` | `/api/v1/video/projects/{project}/revision/regenerate-visual` | `videoRegenerateVisual` | `video:edit` | idempotency=required; concurrency=required |
| `PUT` | `/api/v1/video/projects/{project}/revision/presenter` | `videoShowPresenter` | `video:edit` | idempotency=required; concurrency=required |
| `DELETE` | `/api/v1/video/projects/{project}/revision/items/{item}` | `videoDiscardEdit` | `video:edit` | idempotency=required; concurrency=required |
| `POST` | `/api/v1/video/projects/{project}/revision/apply` | `videoApplyRevision` | `video:publish` | idempotency=required; concurrency=required |

## Voices

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/channels/{channel}/voices` | `listChannelVoices` | `voices:read` | read |
| `POST` | `/api/v1/channels/{channel}/voices/validate` | `validateVoiceProfile` | `voices:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/channels/{channel}/voices/commit` | `commitVoiceProfile` | `voices:write` | idempotency=required; concurrency=optional |
| `GET` | `/api/v1/channels/{channel}/voices/{voice}` | `getVoiceProfile` | `voices:read` | read |

## Webhooks

| Method | Path | Operation | Abilities | Safety |
|---|---|---|---|---|
| `GET` | `/api/v1/webhooks` | `listWebhooks` | `webhooks:read` | read |
| `POST` | `/api/v1/webhooks` | `createWebhook` | `webhooks:write` | idempotency=unsupported; concurrency=unsupported |
| `GET` | `/api/v1/webhooks/{webhook}` | `getWebhook` | `webhooks:read` | read |
| `PUT` | `/api/v1/webhooks/{webhook}` | `updateWebhook` | `webhooks:write` | idempotency=unsupported; concurrency=unsupported |
| `DELETE` | `/api/v1/webhooks/{webhook}` | `deleteWebhook` | `webhooks:write` | idempotency=unsupported; concurrency=unsupported |
| `POST` | `/api/v1/webhooks/{webhook}/test` | `testWebhook` | `webhooks:write` | idempotency=unsupported; concurrency=unsupported |
