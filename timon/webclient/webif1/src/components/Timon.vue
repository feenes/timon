<template>
<div id="timon">
<h1>{{name}}</h1>
<div id="buttons"><button v-on:click="refresh()">Refresh</button></div>
<h2>Simple Minemap</h2>
<div>Probe Age {{ probeAge }} </div>
<div>Last State: {{ lastUpd }} </div>
<div>Selected Probe:
  <span>host: {{ actProbe.host }} </span>
  <span>probe: {{ actProbe.probe }} </span>
  <span>age: {{ actProbe.age }}s </span>
  <span>state: {{ actProbe.state }} </span>
</div>
<div>Probe Message:<br/>
  <tt>{{ actProbe.msg }} </tt>
</div>

<table id="minemap" border="1">
<tr style="line-height: 150px"><th>host</th>
<th v-for="probe in probes" class="rotate"><div>{{probe}}</div></th>
</tr>
<tr v-for="host in hosts">
<td>{{host}}</td>
<td v-for="probe in probes" v-bind:class="{ 
    err: isErrorState(host, probe), 
    unknown: isUnknownState(host, probe),
    warn: isWarningState(host, probe)
    }"
    v-bind:title="msgStr(host, probe)"
    v-on:click="setActProbe(host, probe)"
    >{{shortMinemapStr(host, probe)}}</td>
</tr>
</table><br/>

<h2>hostlist</h2>
<table id="hostlist">
<thead>
<tr><th>host</th><th>addr</th>
</tr>
</thead>
<tbody>
<tr v-for="host in hosts"><td>{{host}}</td><td> {{hostcfg[host].addr}}</td>
</tr>
</tbody>
</table>


</div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'timon',
  data: function() {
    return {
      lastUpd: Date.now(),
      probeAge: 0,
      mtime: "-",
      _state: {}, // temporary full timon state
      _hosts: [], // temporary list of hosts
      state: {}, // full timon state
      hosts: [], // list of hosts
      name: 'Timon Web Interface 1',
      cfg: {}, // full timon config
      hostcfg: {}, // timon hosts config
      probemap: [], // short probename to full probename
      minemap: {},
      actProbe: {
        host: "-",
        probe: "-",
        age: "-",
        state: "-",
        msg: "-"
        },
    }
  },
  methods: {
    setActProbe(host, probename) {
        var info = this.minemapInfo(host, probename);
        var probe = this.actProbe;
        probe.host = host;
        probe.probe = probename;
        probe.age = (this.lastUpd - info.age).toFixed(0);
        probe.state = info.state;
        probe.msg = info.msg;
    },
    minemapInfo(host, probename) {
      var probeName = this.minemap[host][probename];
      var result = "+";
      var probeStates;
      var probeState;
      var probelen;
      var statestr = "#";
      var rslt = {
        age: "?",
        state: statestr,
        msg: "",
      };
      if (typeof probeName === "undefined"){
          rslt.state =  '-';
          return rslt;
      }
      probeStates = this.state.probe_state[probeName];
      probelen = probeStates.length; 
      if (probelen == 0){
        rslt.state = "?";
        return rslt;
      } else {
        probeState = probeStates[probelen-1];
        rslt.age = probeState[0] - this.probeAge;
        rslt.state = probeState[1];
        rslt.msg = probeState[2];
      }
      return rslt;
    },
    msgStr(host, probename) {
        var rslt = this.minemapInfo(host, probename);
        return rslt.msg;
    },
    minemapStr(host, probename) {
        var rslt = this.minemapInfo(host, probename);
        return rslt.state;
    },
    shortMinemapStr(host, probename) {
        var minemapstr = this.minemapStr(host, probename);
        return minemapstr.substring(0,3);
    },
    isErrorState(host, probename) {
        return this.shortMinemapStr(host, probename) == "ERR";
    },
    isWarningState(host, probename) {
        return this.shortMinemapStr(host, probename) == "WAR";
    },
    isUnknownState(host, probename) {
        return this.shortMinemapStr(host, probename) == "UNK";
    },
    mk_minemap_cfg(state) {
        var host, cfg;
        var probes = this.probes = {};
        var probemap = this.probemap = {};
        var hosts = this.hosts;
        var full_probename, probename;
        var minemap = this.minemap = {};
        for(let[host, cfg] of Object.entries(state.hosts)){
            console.log("host", host, cfg);
            probemap[host] = {}
            minemap[host] = {}
            for (full_probename of cfg.probes){
                probename = state.all_probes[full_probename]['probe'];
                console.log(full_probename, probename);
                probes[probename] = probename;
                probemap[host][probename] = {
                   full_name: full_probename,
                   short_name: probename
                }
                minemap[host][probename] = full_probename;
            }
        }
    },
    parse_cfg(cfg) {
        // make host list
        this.cfg = cfg;
        console.log("cfg", cfg);
        var hosts = this.hosts = [];
        this.hostcfg = cfg.hosts;
        var host, hostcfg;
        for(let[host, hostcfg] of Object.entries(cfg.hosts)){
            console.log("host", host, hostcfg);
            hosts.push(host);
        }
        console.log("hosts", hosts);
        this.mk_minemap_cfg(cfg);
        return;
    },
    mkMinemap(state){
    },
    parse_state(state) {
        this.mkMinemap(state);
    },
    parse_cfg_state(cfg, state){
      this.cfg = cfg
      this.state = state
      this.parse_cfg(cfg);
      this.parse_state(state);
      this.lastUpd = Date.now()/1000;
      this.mtime = state.mtime;
      this.probeAge = this.lastUpd - state.mtime;
    },
    refresh() {
       this._cfg = null;
       this._state = null;

      console.log("refreshing", this.name);
      axios.get('../timoncfg_state.json')
      .then(response => {
        var _cfg = this._cfg = response.data;
        console.log("got cfg", _cfg);
        if (_cfg && this._state){
          this.parse_cfg_state(_cfg, this._state);
        }
      })
      .catch(e => {
        console.log("error: ", e);
      });
      axios.get('../timon_state.json')
      .then(response => {
        var _state = this._state = response.data;
        console.log("got state", _state);
        if (_state && this._cfg){
          this.parse_cfg_state(this._cfg, _state);
        }
      })
      .catch(e => {
        console.log("error: ", e);
      });
    }
  },
  mounted: function() {
    console.log("mounted", this.name);
    this.refresh();
  }
}
</script>
