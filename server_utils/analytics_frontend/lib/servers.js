import api from './api'

export const fetchPublicServers = (query) => api.get('/api/groups/public/list' + (query ? `?query=${encodeURIComponent(query)}` : '')).then(r=>r.data)
export const deleteGroup = (group_id) => api.delete(`/api/groups/delete?group_id=${encodeURIComponent(group_id)}`).then(r=>r.data)

export default { fetchPublicServers, deleteGroup }
