
(function () {

    var checkMatch, i, iframes, importVideos, inject, l, typeMap;

    importVideos = function (args) {
        var a, qs;
        qs = [];
        a = void 0;
        for (a in args) {
            if (args.hasOwnProperty(a)) {
                qs.push(a + "=" + args[a]);
            }
        }
        inject(qs.join("&"));
        return true;
    };

    checkMatch = function (re, str) {
        var match;
        match = re.exec(str || window.location);
        if (match) {
            return importVideos({
                source: match[1],
                type: typeMap[match[2]] || match[2],
                id: match[3]
            });
        }
    };


    inject = function (video) {
        var css, newIframe;
        newIframe = document.createElement('iframe');
        newIframe.src = '{{iframe_url}}?' + video;
        newIframe.id = 'rockpackiframe';
        newIframe.name = "rockpackiframe";
        newIframe.style['position'] = 'fixed';
        newIframe.style['width'] = '100%';
        newIframe.style['height'] = '100%';
        newIframe.style['top'] = '0';
        newIframe.style['left'] = '0';
        newIframe.style['z-index'] = '5000';
        newIframe.setAttribute('allowtransparency', 'true');
        newIframe.style.display = "none";
        document.body.appendChild(newIframe);

        fix_flash();

        if (!window.addEventListener) {
            window.attachEvent("onmessage", receiveMessage);
        } else {
            window.addEventListener('message', receiveMessage, false);
        }

        if (window.addEventListener) {
            newIframe.addEventListener("load", showiframe, false);
        } else if (window.attachEvent) {
            newIframe.attachEvent("onload", showiframe);
        }
    }

    showiframe = function () {
        document.getElementById("rockpackiframe").style.display = "block";
    }

    receiveMessage = function (evt) {
        var element;
        element = document.getElementById("rockpackiframe");
        element.parentNode.removeChild(element);
        if (!window.addEventListener) {
            window.detachEvent("onmessage", receiveMessage);
        } else {
            window.removeEventListener('message', receiveMessage, false);
        }
    }


    fix_flash = function () {
        // loop through every embed tag on the site
        var embeds = document.getElementsByTagName('embed');
        for (i = 0; i < embeds.length; i++) {
            embed = embeds[i];
            var new_embed;
            // everything but Firefox & Konqueror
            if (embed.outerHTML) {
                var html = embed.outerHTML;
                // replace an existing wmode parameter
                if (html.match(/wmode\s*=\s*('|")[a-zA-Z]+('|")/i))
                    new_embed = html.replace(/wmode\s*=\s*('|")window('|")/i, "wmode='transparent'");
                // add a new wmode parameter
                else
                    new_embed = html.replace(/<embed\s/i, "<embed wmode='transparent' ");
                // replace the old embed object with the fixed version
                embed.insertAdjacentHTML('beforeBegin', new_embed);
                embed.parentNode.removeChild(embed);
            } else {
                // cloneNode is buggy in some versions of Safari & Opera, but works fine in FF
                new_embed = embed.cloneNode(true);
                if (!new_embed.getAttribute('wmode') || new_embed.getAttribute('wmode').toLowerCase() == 'window')
                    new_embed.setAttribute('wmode', 'transparent');
                embed.parentNode.replaceChild(new_embed, embed);
            }
        }
        // loop through every object tag on the site
        var objects = document.getElementsByTagName('object');
        for (i = 0; i < objects.length; i++) {
            object = objects[i];
            var new_object;
            // object is an IE specific tag so we can use outerHTML here
            if (object.outerHTML) {
                var html = object.outerHTML;
                // replace an existing wmode parameter
                if (html.match(/<param\s+name\s*=\s*('|")wmode('|")\s+value\s*=\s*('|")[a-zA-Z]+('|")\s*\/?\>/i))
                    new_object = html.replace(/<param\s+name\s*=\s*('|")wmode('|")\s+value\s*=\s*('|")window('|")\s*\/?\>/i, "<param name='wmode' value='transparent' />");
                // add a new wmode parameter
                else
                    new_object = html.replace(/<\/object\>/i, "<param name='wmode' value='transparent' />\n</object>");
                // loop through each of the param tags
                var children = object.childNodes;
                for (j = 0; j < children.length; j++) {
                    if (children[j].getAttribute('name').match(/flashvars/i)) {
                        new_object = new_object.replace(/<param\s+name\s*=\s*('|")flashvars('|")\s+value\s*=\s*('|")[^'"]*('|")\s*\/?\>/i, "<param name='flashvars' value='" + children[j].getAttribute('value') + "' />");
                    }
                }
                // replace the old embed object with the fixed versiony
                object.insertAdjacentHTML('beforeBegin', new_object);
                object.parentNode.removeChild(object);
            }
        }
    }


    typeMap = {
        v: "video",
        embed: "video",
        list: "playlist"
    };

    iframes = void 0;
    i = void 0;
    l = void 0;
    if (checkMatch(/(youtube)\.com\S*(v)=([\w\-]{11})/)) {
        return;
    }
    if (checkMatch(/(youtube)\.com\/(user)\/(\w+)/)) {
        return;
    }
    if (checkMatch(/(youtube)\.com\S*(list)=([\w\-]+)/)) {
        return;
    }
    iframes = document.getElementsByTagName("iframe");
    i = 0;
    l = iframes.length;
    while (i < l) {
        if (checkMatch(/(youtube)\.com\/(embed)\/([\w\-]{11})/, iframes[i].src)) {
            return;
        }
        i++;
    }
    return window.alert("No video found");
})();