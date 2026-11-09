/* Channel-only identity, English controls and reliable section navigation. */
(() => {
    'use strict';
    const basePattern=/^(\/(?:@[^/]+|(?:channel|c|user)\/[^/]+))(?:\/(.*))?\/?$/;
    const tabsSelector='yt-tab-shape,tp-yt-paper-tab,ytd-expandable-tab-renderer,[role="tab"]';
    const aboutSelector='ytd-about-channel-renderer,yt-about-channel-renderer,ytd-channel-about-metadata-renderer,yt-about-channel-view-model';
    const compact=new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:2});
    const words=new Map([
        ['Subscribe','Подписаться','Abonnieren'],['Subscribed','Вы подписаны','Подписка оформлена','Abonniert'],
        ['Unsubscribe','Отписаться','Abo beenden'],['Cancel','Отмена','Abbrechen'],['Confirm','Подтвердить','Bestätigen'],
        ['More','Ещё','Еще','Mehr'],['Show more','Показать полностью'],['Show less','Свернуть','Weniger anzeigen'],
        ['Latest','Новые','Недавние','Сначала новые','Neueste'],['Popular','Популярные','Beliebt'],['Oldest','Старые','Сначала старые','Älteste'],
        ['Play all','Смотреть все','Воспроизвести все','Alle wiedergeben'],['Join','Спонсировать','Mitglied werden'],
        ['Share','Поделиться','Teilen'],['All','Все','Alle'],['Personalized','На основе предпочтений','Personalisiert'],
        ['None','Никакие','Keine'],['Notifications','Уведомления','Benachrichtigungen'],['Search','Поиск','Suchen'],
        ['Customize channel','Настроить вид канала','Kanal anpassen'],['Manage videos','Управление видео','Videos verwalten'],
        ['Created playlists','Созданные плейлисты','Erstellte Playlists'],['Sort by','Сортировать','Sortieren nach'],
    ].flatMap(([english,...labels])=>labels.map(label=>[label.toLocaleLowerCase(),english])));
    const sections=[
        ['videos','Videos',/^(videos|видео)$/iu],['streams','Live',/^(live|streams|трансляции|livestreams)$/iu],
        ['playlists','Playlists',/^(playlists|плейлисты)$/iu],['posts','Posts',/^(posts|community|посты|записи|сообщество|beiträge)$/iu],
        ['search','Search',/^(search(?: this channel)?|поиск(?: на канале)?|suchen|kanalsuche)$/iu],
    ];
    function count(value,kind){
        const unit='(thousand|million|billion|trillion|тыс\\.?|млн\\.?|млрд\\.?|трлн\\.?|Tsd\\.?|Mio\\.?|Mrd\\.?|[kmbt])?';
        const label=kind==='subscribers'?'(?:subscribers?|подписчик[а-яё]*|Abonnenten)':'(?:videos?|видео|ролик[а-яё]*)';
        const source=String(value||'').replace(/[\u00a0\u202f]/g,' ').trim();
        const match=source.match(new RegExp('(\\d[\\d\\s.,]*?)\\s*'+unit+'\\s*'+label+'(?=$|[\\s·•*])','iu'));
        if(!match)return '';
        let amount=match[1].replace(/\s/g,''),suffix=(match[2]||'').toLowerCase().replace(/\.$/,'');
        if(!suffix&&/^\d{1,3}(?:[.,]\d{3})+$/.test(amount))amount=amount.replace(/[.,]/g,'');
        else{const decimal=Math.max(amount.lastIndexOf('.'),amount.lastIndexOf(','));if(decimal>=0)amount=amount.slice(0,decimal).replace(/[.,]/g,'')+'.'+amount.slice(decimal+1);}
        const power=/^(k|thousand|тыс|tsd)$/.test(suffix)?3:/^(m|million|млн|mio)$/.test(suffix)?6:/^(b|billion|млрд|mrd)$/.test(suffix)?9:/^(t|trillion|трлн)$/.test(suffix)?12:0;
        const number=Number(amount)*10**power;if(!Number.isFinite(number))return '';
        return compact.formatToParts(number).map(part=>part.type==='compact'?' '+part.value:part.value).join('');
    }
    const svg=kind=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">${kind==='subscribers'?'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>':'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3Z"/>'}</svg>`;
    class Channel {
        static landing(url){
            const match=url.pathname.match(basePattern);
            if(!match||match[2]&&!/^(featured)?\/?$/.test(match[2]))return null;
            const target=new URL(url);target.pathname=match[1]+'/videos';target.searchParams.set('hl','en');target.searchParams.set('persist_hl','1');return target.href;
        }
        static destination(url,language){
            const landing=Channel.landing(url);if(landing)return landing;
            if(!basePattern.test(url.pathname)||!language||/^en(?:-|$)/i.test(language)||url.searchParams.get('hl')==='en')return null;
            const target=new URL(url);target.searchParams.set('hl','en');target.searchParams.set('persist_hl','1');return target.href;
        }
        constructor(){
            this.hidden=new Set();this.text=new Map();this.attributes=new Map();this.aboutNodes=new Map();
            this.stats=document.createElement('div');this.stats.id='myt-channel-stats';this.stats.lang='en';
            this.stats.attachShadow({mode:'open'}).innerHTML='<style>:host{display:block;color:var(--myt-muted);font:14px/1.6 Arial,sans-serif}.row{display:flex;align-items:center;flex-wrap:wrap;gap:0 8px}.metric{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}svg{width:15px;height:15px;flex:none}[hidden]{display:none!important}</style><div class="row"></div>';
            this.nav=document.createElement('div');this.nav.id='myt-channel-nav';this.nav.lang='en';
            this.nav.attachShadow({mode:'open'}).innerHTML=`<style>
                :host{display:block!important;min-width:0;font:600 16px/1.4 Arial,sans-serif;color:var(--myt-ink)}*{box-sizing:border-box}[hidden]{display:none!important}
                nav{display:flex;justify-content:center;gap:8px;overflow-x:auto;scrollbar-width:thin;padding:4px 0}a,button{flex:none;color:inherit;font:inherit;text-decoration:none;background:none;border:0;border-bottom:2px solid transparent;padding:12px 16px;cursor:pointer;white-space:nowrap}
                [aria-current=page],button[aria-expanded=true]{border-color:currentColor}a:hover,button:hover{background:var(--myt-soft);border-radius:8px 8px 0 0}a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid currentColor;outline-offset:-2px}
                form{display:flex;gap:8px;max-width:520px;margin:8px auto;padding:0 8px}input{min-width:0;flex:1;border:1px solid var(--myt-border);border-radius:8px;background:var(--myt-surface);color:inherit;padding:10px 12px;font:400 16px Arial,sans-serif}
                @media(max-width:600px){nav{gap:0;justify-content:safe center}a,button{font-size:14px;padding:12px 9px}}
                </style><nav aria-label="Channel sections"></nav><form role="search" hidden><input name="query" type="search" aria-label="Search this channel" placeholder="Search this channel" autocomplete="off"><button type="submit">Search</button></form>`;
            this.nav.shadowRoot.querySelector('form').addEventListener('submit',event=>{
                event.preventDefault();event.stopPropagation();
                const query=this.nav.shadowRoot.querySelector('input').value.trim();if(query)this.open(this.url('search',query));
            });
            this.click=event=>{
                if(!event.composedPath().includes(this.nav))return;
                const link=event.composedPath().find(node=>node instanceof HTMLAnchorElement);
                if(!link){
                    const button=event.composedPath().find(node=>node instanceof HTMLButtonElement);
                    if(button){event.stopImmediatePropagation();if(button.dataset.section==='search'){event.preventDefault();this.toggleSearch(button);}}
                    return;
                }
                // Keep browser navigation independent of stale YouTube SPA tab commands.
                event.stopImmediatePropagation();
                if(!event.button&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey){event.preventDefault();this.open(link.href);}
            };
            window.addEventListener('click',this.click,true);
            window.addEventListener('auxclick',this.click,true);
        }
        toggleSearch(button){const form=this.nav.shadowRoot.querySelector('form');form.hidden=!form.hidden;button.setAttribute('aria-expanded',String(!form.hidden));if(!form.hidden)form.querySelector('input').focus();}
        open(href){location.assign(href);}
        url(section,query){const url=new URL(this.base+'/'+section,location.origin);url.searchParams.set('hl','en');url.searchParams.set('persist_hl','1');if(query)url.searchParams.set('query',query);return url.href;}
        hide(node){if(node&&!this.hidden.has(node)){node.setAttribute('data-myt-channel-source','');this.hidden.add(node);}}
        sync(browse){
            const match=location.pathname.match(basePattern);if(!match)return;
            this.base=match[1];
            const header=browse.querySelector(':scope > #header,:scope > #page-header,ytd-c4-tabbed-header-renderer,yt-page-header-view-model,yt-page-header-renderer');
            if(header){this.identity(header);this.links(header);}
            this.navigation(browse,match[2]?.replace(/\/$/,'')||'videos');
            this.about();
            this.translate(browse);
            for(const node of [...this.hidden])if(!node.isConnected){node.removeAttribute('data-myt-channel-source');this.hidden.delete(node);}
            for(const node of this.text.keys())if(!node.isConnected)this.text.delete(node);
            for(const node of this.attributes.keys())if(!node.isConnected)this.attributes.delete(node);
            for(const [node,names]of this.aboutNodes)if(!node.isConnected){for(const name of names)node.removeAttribute(name);this.aboutNodes.delete(node);}
        }
        identity(header){
            const candidates=[...header.querySelectorAll('yt-content-metadata-view-model,#channel-tagline,#channel-handle,#subscriber-count,#subscribers,#videos-count,#video-count')];
            const values=candidates.map(node=>node.textContent.replace(/\s+/g,' ').trim());
            const handle=values.map(value=>value.match(/@[^\s·•*]+/u)?.[0]).find(Boolean)||(this.base.startsWith('/@')?decodeURI(this.base.slice(1)):'');
            const subscribers=values.map(value=>count(value,'subscribers')).find(Boolean)||'';
            const videos=values.map(value=>count(value,'videos')).find(Boolean)||'';
            const first=candidates.find(node=>node.matches('yt-content-metadata-view-model,#channel-tagline'))||candidates[0];
            if(first&&(handle||subscribers||videos)){
                if(this.stats.previousElementSibling!==first)first.after(this.stats);
                const signature=JSON.stringify([handle,subscribers,videos]);
                if(this.stats.dataset.value!==signature){
                    this.stats.dataset.value=signature;const row=this.stats.shadowRoot.querySelector('.row');row.replaceChildren();
                    const add=part=>{if(row.childNodes.length){const separator=document.createElement('span');separator.textContent='·';separator.setAttribute('aria-hidden','true');row.append(separator);}row.append(part);};
                    if(handle){const span=document.createElement('span');span.textContent=handle;add(span);}
                    for(const [kind,value]of [['subscribers',subscribers],['videos',videos]])if(value){const span=document.createElement('span');span.className='metric';span.dataset.kind=kind;span.setAttribute('aria-label',value+' '+kind);const number=document.createElement('span');number.textContent=value;span.append(number);span.insertAdjacentHTML('beforeend',svg(kind));add(span);}
                }
                for(const node of candidates)this.hide(node);
            }else this.stats.remove();
        }
        links(header){
            // Some headers render the external-link row as attribution instead
            // of a channel-external-link view model. Redirect URLs are links too.
            const protectedContent='h1,#channel-name,ytd-channel-name,#avatar,yt-avatar-shape,img,yt-content-metadata-view-model,#channel-tagline,#myt-channel-stats,#myt-channel-nav,yt-description-preview-view-model,#description-container,#channel-description,ytd-subscribe-button-renderer,yt-subscribe-button-view-model';
            for(const anchor of header.querySelectorAll('a[href]')){
                if(anchor.closest(protectedContent)||anchor.querySelector('img'))continue;
                let url;try{url=new URL(anchor.href);if(url.pathname==='/redirect'&&/(^|\.)youtube\.com$/.test(url.hostname))url=new URL(url.searchParams.get('q')||url.searchParams.get('url'));}catch{continue;}
                if(!/^https?:$/.test(url.protocol)||/(^|\.)youtube\.com$/.test(url.hostname))continue;
                let row=anchor;
                for(let parent=anchor.parentElement;parent&&parent!==header;parent=parent.parentElement){
                    if(parent.matches(protectedContent)||parent.querySelector(protectedContent))break;
                    row=parent;
                }
                this.hide(row);
            }
        }
        markAbout(node,part){
            if(!node)return;
            const name='data-myt-channel-about'+(part?'-'+part:'');
            if(!node.hasAttribute(name))node.setAttribute(name,'');
            if(!this.nextAboutNodes.has(node))this.nextAboutNodes.set(node,new Set());
            this.nextAboutNodes.get(node).add(name);
        }
        aboutInfoValue(row){
            const content=row.cloneNode(true);
            content.querySelectorAll('yt-icon,svg,img,tp-yt-paper-tooltip,yt-tooltip,[aria-hidden="true"],script,style').forEach(node=>node.remove());
            if(content.textContent.trim())return true;
            return !!row.querySelector('a[href^="mailto:"],a[href^="tel:"]')||[...row.querySelectorAll('button,[role="button"]')].some(button=>/e-?mail|почт|anzeigen|reveal/iu.test(button.getAttribute('aria-label')||''));
        }
        aboutLinks(source,scope){
            const rowSelector='yt-channel-external-link-view-model,yt-channel-external-link-renderer,ytd-channel-external-link-renderer,.ytChannelExternalLinkViewModelHost';
            const rows=[...source.querySelectorAll(rowSelector+',#primary-links > a')].filter(row=>!row.parentElement.closest(rowSelector));
            const sections=new Set(source.querySelectorAll('#links-section,#links-container,#primary-links,.ytAboutChannelViewModelLinks'));
            const headings=new Map();
            for(const heading of source.querySelectorAll('h2,h3,[role="heading"]')){
                if(!/^(links|ссылки)$/iu.test(heading.textContent.trim()))continue;
                const section=heading.parentElement===source?heading.nextElementSibling:heading.parentElement;
                if(!section||section.matches('h2,h3,[role="heading"]')){this.markAbout(heading,'empty');continue;}
                sections.add(section);headings.set(section,heading);
            }
            if(!this.aboutLinkSignatures.has(scope))this.aboutLinkSignatures.set(scope,new Map());
            const seen=this.aboutLinkSignatures.get(scope);
            const destination=row=>{
                const anchor=row.matches('a[href]')?row:row.querySelector('a[href]');if(!anchor)return '';
                try{
                    let url=new URL(anchor.href);
                    if(/(^|\.)youtube\.com$/.test(url.hostname)&&url.pathname==='/redirect')url=new URL(url.searchParams.get('q')||url.searchParams.get('url'));
                    return /^(https?|mailto|tel):$/.test(url.protocol)?url.href:'';
                }catch{return '';}
            };
            // A native fallback can keep another Links heading and an empty
            // list, or a second hydrated copy with different redirect tokens.
            for(const section of sections){
                if([...sections].some(parent=>parent!==section&&parent.contains(section)))continue;
                this.markAbout(section,'links');
                const items=rows.filter(row=>section.contains(row));
                const keys=[...new Set(items.map(destination).filter(Boolean))].sort();
                const nativeHidden=section.closest('[hidden],[aria-hidden="true"]')||section.style.display==='none';
                const signature=keys.length?JSON.stringify(keys):'';
                const previous=signature&&seen.get(signature);
                const empty=!items.some(row=>destination(row)||row.textContent.trim());
                if(nativeHidden||empty||previous&&previous!==section){
                    this.markAbout(section,'empty');
                    const heading=headings.get(section);if(heading&&!section.contains(heading))this.markAbout(heading,'empty');
                }else if(signature)seen.set(signature,section);
            }
            for(const row of rows){
                this.markAbout(row,'link');this.markAbout(row.parentElement,'link-list');
                this.markAbout(row.querySelector('#icon,yt-icon,yt-img-shadow,yt-image,img,.ytChannelExternalLinkViewModelIcon,.yt-channel-external-link-view-model-wiz__icon'),'icon');
            }
        }
        about(){
            this.nextAboutNodes=new Map();
            this.aboutLinkSignatures=new Map();
            const sources=new Set(document.querySelectorAll(aboutSelector));
            for(const panel of document.querySelectorAll('[target-id="engagement-panel-channel-about"],[data-target-id="engagement-panel-channel-about"]')){
                if(!panel.querySelector(aboutSelector)){
                    const content=panel.querySelector(':scope > #content');
                    if(content)sources.add(content.firstElementChild||content);
                }
            }
            for(const source of sources){
                // Decorate the existing dialog; native links, email verification,
                // focus handling and the close controls retain their DOM nodes.
                this.markAbout(source,'');
                let dialog=null,panel=null;
                for(let parent=source.parentElement;parent&&!parent.matches('ytd-popup-container,body');parent=parent.parentElement){
                    if(parent.matches('dialog,tp-yt-paper-dialog,[role="dialog"]'))dialog=parent;
                    if(parent.matches('ytd-engagement-panel-section-list-renderer')){panel=parent;this.markAbout(parent,'frame');}
                }
                if(dialog)this.markAbout(dialog,'dialog');
                const frame=panel||dialog;
                const scroll=frame?.querySelector(':scope > #content,:scope > #contents,:scope > #contentWrapper')||source;
                this.markAbout(scroll,'scroll');
                for(const description of source.querySelectorAll('#description-container,#channel-description,#description,.ytAboutChannelViewModelDescription')){
                    if(!description.parentElement.closest('[data-myt-channel-about-description]'))this.markAbout(description,'description');
                }
                this.aboutLinks(source,dialog||panel||source);
                for(const heading of source.querySelectorAll('h2,h3,[role="heading"]')){
                    const label=heading.textContent.trim();
                    if(/^(more info|channel details|дополнительная информация|сведения о канале)$/iu.test(label))this.markAbout(heading.parentElement===source?heading.nextElementSibling:heading.parentElement,'info');
                }
                for(const info of source.querySelectorAll('#additional-info-container,#metadata-container,#more-info,.ytAboutChannelViewModelMoreInfo'))this.markAbout(info,'info');
                for(const info of source.querySelectorAll('[data-myt-channel-about-info]')){
                    const rows=[...info.querySelectorAll('tr,yt-about-channel-metadata-view-model,yt-about-channel-info-row-view-model,.ytAboutChannelViewModelMetadataRow,.metadata-row,.info-row')];
                    for(const row of rows){
                        this.markAbout(row,'info-row');this.markAbout(row.parentElement,'info-list');
                        if(!this.aboutInfoValue(row))this.markAbout(row,'empty');
                        this.markAbout(row.querySelector('yt-icon,yt-img-shadow,yt-image,img,svg'),'icon');
                    }
                }
            }
            for(const [node,names]of this.aboutNodes)for(const name of names)if(!this.nextAboutNodes.get(node)?.has(name))node.removeAttribute(name);
            this.aboutNodes=this.nextAboutNodes;this.nextAboutNodes=null;this.aboutLinkSignatures=null;
        }
        navigation(browse,current){
            const tabs=[...browse.querySelectorAll(tabsSelector)].filter(node=>!node.parentElement.closest(tabsSelector));
            if(!tabs.length){this.nav.remove();return;}
            const group=tabs[0].closest('yt-tab-group-shape,tp-yt-paper-tabs')||tabs[0];
            if(this.nav.nextElementSibling!==group)group.before(this.nav);
            const available=new Map();
            for(const tab of tabs){
                const label=tab.textContent.trim()||tab.getAttribute('aria-label')||tab.querySelector('[aria-label]')?.getAttribute('aria-label')||'';
                const anchor=tab.matches('a[href]')?tab:tab.querySelector('a[href]');
                let slug='';try{slug=new URL(anchor?.href||tab.getAttribute('href')||'/',location.href).pathname.split('/').filter(Boolean).at(-1)||'';}catch{}
                const section=sections.find(([key,,pattern])=>key===slug||key==='posts'&&slug==='community'||pattern.test(label)||key==='search'&&tab.matches('ytd-expandable-tab-renderer'));
                if(section)available.set(section[0],{key:section[0],label:section[1],slug:section[0]==='posts'&&slug==='community'?'community':section[0]});
            }
            if(!available.size){
                this.nav.remove();
                for(const node of [...tabs,group]){node.removeAttribute('data-myt-channel-source');this.hidden.delete(node);}
                return;
            }
            for(const tab of tabs)this.hide(tab);
            // Hide the native scroller too, so it cannot reserve an empty row.
            if(group!==tabs[0])this.hide(group);
            const items=sections.map(([key])=>available.get(key)).filter(Boolean),signature=JSON.stringify([this.base,items]);
            if(this.nav.dataset.items!==signature){
                this.nav.dataset.items=signature;const nav=this.nav.shadowRoot.querySelector('nav');nav.replaceChildren();
                for(const item of items){
                    const control=document.createElement(item.key==='search'?'button':'a');control.textContent=item.label;control.dataset.section=item.key;
                    if(item.key==='search'){
                        control.type='button';control.setAttribute('aria-expanded','false');
                    }else control.href=this.url(item.slug);
                    nav.append(control);
                }
            }
            for(const link of this.nav.shadowRoot.querySelectorAll('nav a')){
                const selected=link.dataset.section===(current==='community'?'posts':current);
                if(selected)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
            }
            if(current==='search'&&this.current!=='search'){
                this.nav.shadowRoot.querySelector('form').hidden=false;
                this.nav.shadowRoot.querySelector('input').value=new URL(location.href).searchParams.get('query')||'';
                this.nav.shadowRoot.querySelector('nav button')?.setAttribute('aria-expanded','true');
            }
            this.current=current;
        }
        translate(browse){
            const scopes=[...browse.querySelectorAll(':scope > #header,:scope > #page-header,ytd-feed-filter-chip-bar-renderer,yt-chip-cloud-renderer'),...document.querySelectorAll('ytd-popup-container [role="menuitem"],ytd-confirm-dialog-renderer')];
            for(const scope of scopes){
                const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);let node;
                while(node=walker.nextNode()){
                    const parent=node.parentElement;
                    if(!parent||parent.closest('h1,#channel-name,ytd-channel-name,#channel-tagline,yt-content-metadata-view-model,#myt-channel-nav,#myt-channel-stats'))continue;
                    const description=parent.closest('#description-container,#channel-description,yt-description-preview-view-model');
                    if(description&&!parent.closest('button,[role="button"],.ytDescriptionPreviewViewModelMoreButton,.ytDescriptionPreviewViewModelMoreText,.yt-description-preview-view-model-wiz__more-button'))continue;
                    const translated=words.get(node.data.trim().replace(/^[.…\s]+/u,'').toLocaleLowerCase());if(!translated)continue;
                    this.text.set(node,{original:node.data,applied:translated});node.data=translated;
                }
                for(const element of scope.querySelectorAll('[aria-label],[title],[placeholder]'))for(const name of ['aria-label','title','placeholder']){
                    if(element.closest('h1,#channel-name,ytd-channel-name'))continue;
                    const original=element.getAttribute(name),translated=words.get(original?.trim().toLocaleLowerCase());if(!translated)continue;
                    if(!this.attributes.has(element))this.attributes.set(element,new Map());this.attributes.get(element).set(name,{original,applied:translated});element.setAttribute(name,translated);
                }
            }
        }
        destroy(){
            window.removeEventListener('click',this.click,true);window.removeEventListener('auxclick',this.click,true);this.nav.remove();this.stats.remove();
            for(const node of this.hidden)node.removeAttribute('data-myt-channel-source');this.hidden.clear();
            for(const [node,names]of this.aboutNodes)for(const name of names)node.removeAttribute(name);this.aboutNodes.clear();
            for(const [node,state]of this.text)if(node.data===state.applied)node.data=state.original;
            for(const [node,attrs]of this.attributes)for(const [name,state]of attrs)if(node.getAttribute(name)===state.applied)node.setAttribute(name,state.original);
            this.text.clear();this.attributes.clear();
        }
    }
    globalThis.MinimalYouTubeChannel=Channel;
})();
