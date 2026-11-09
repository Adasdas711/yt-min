/* Read the channel's public description in MAIN; no commands or credentials. */
(() => {
    'use strict';
    const channelBase=path=>path.match(/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))/)?.[1]?.toLowerCase()||'';
    const label=value=>typeof value==='string'?value:typeof value?.content==='string'?value.content:typeof value?.simpleText==='string'?value.simpleText:Array.isArray(value?.runs)?value.runs.map(run=>run.text||'').join(''):'';
    document.addEventListener('minimal-youtube:channel-description',event=>{
        const source=event.target,base=channelBase(location.pathname);
        if(!base||!(source instanceof Element)||!source.closest('ytd-browse[page-subtype="channels"]'))return;
        let description='';
        for(const data of [source.data,source.viewModel,source.__data?.data,source.polymerController?.data]){
            description=label(data?.descriptionPreviewViewModel?.description)||label(data?.description)||label(data?.descriptionText);
            if(description)break;
        }
        let fullDescription='';
        const app=document.querySelector('ytd-app');
        for(const metadata of [app?.data?.response?.metadata?.channelMetadataRenderer,app?.data?.metadata?.channelMetadataRenderer,globalThis.ytInitialData?.metadata?.channelMetadataRenderer]){
            if(!metadata)continue;
            const matches=[metadata.vanityChannelUrl,metadata.channelUrl].some(value=>{if(typeof value!=='string'||!value.trim())return false;try{return channelBase(new URL(value,location.href).pathname)===base;}catch{return false;}});
            if(matches&&typeof metadata.description==='string'){fullDescription=metadata.description;break;}
        }
        const snapshot=JSON.stringify({base,description,fullDescription});
        if(source.getAttribute('data-myt-channel-description-data')!==snapshot)source.setAttribute('data-myt-channel-description-data',snapshot);
    });
})();
