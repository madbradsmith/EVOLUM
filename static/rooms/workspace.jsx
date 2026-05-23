/* =====================================================================
   EVOLUM Workspace — uses shared Room shell
   ===================================================================== */
const WorkspaceApp = () => {
  const [selectedProject, setSelectedProject] = React.useState('p01');
  const [projectsView, setProjectsView] = React.useState('grid');
  const project = PROJECTS.find(p => p.id === selectedProject);

  const config = {
    activeTool: 'workspace',
    crumb: 'Overview',
    project,
    rightW: 320,
    bottomH: 200,
    panels: {
      projects:  { mode: 'docked',   zone: 'main',   meta: { title: 'Projects',  icon: 'film',    sub: `${PROJECTS.length} items` } },
      inspector: { mode: 'docked',   zone: 'right',  meta: { title: 'Inspector', icon: 'folder',  sub: '' } },
      activity:  { mode: 'docked',   zone: 'bottom', meta: { title: 'Activity',  icon: 'clock',   sub: <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--ok-glow)'}}/>LIVE · {ACTIVITY.length}</span> } },
      warren:    { mode: 'floating', rect: { x: 0, y: 0, w: 340, h: 360 }, meta: { title: 'Warren', icon: 'sparkle', sub: 'Investor Room' } },
    },
    renderPanel: (id) => {
      switch (id) {
        case 'projects':  return <ProjectsView selected={selectedProject} setSelected={setSelectedProject} view={projectsView} setView={setProjectsView}/>;
        case 'inspector': return <Inspector project={project}/>;
        case 'activity':  return <Activity/>;
        case 'warren':    return <Warren/>;
        default: return null;
      }
    },
    statusItems: [
      { lbl: 'PROJECTS', num: PROJECTS.length },
      { lbl: 'SCRIPT',   num: PROJECTS.filter(p=>p.stage==='script').length },
      { lbl: 'PITCH',    num: PROJECTS.filter(p=>p.stage==='pitch').length },
      { lbl: 'INVEST',   num: PROJECTS.filter(p=>p.stage==='invest').length },
      { lbl: 'DELIVER',  num: PROJECTS.filter(p=>p.stage==='deliver').length },
    ],
    statusRight: (
      <React.Fragment>
        <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--ok-glow)'}}/>Warren online</span>
        <span>$1013.85 / $18.75 wk</span>
        <span>evolumstudio@gmail.com</span>
        <span>EN · v1.4.0</span>
      </React.Fragment>
    ),
  };

  return <Room config={config}/>;
};

ReactDOM.createRoot(document.getElementById('app')).render(<WorkspaceApp/>);
