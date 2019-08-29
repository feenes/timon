<template>
  <div id="timon">
    <h1>{{ name }}</h1>
    <div id="buttons">
      <button
        @click="refresh()"
      >
        Refresh
      </button>
    </div>
    <div
      name="auto"
    >
      <input
        id="auto"
        v-model="autoRefresh"
        name="yay"
        type="checkbox"
      >
      <label for="auto"> Activate auto refresh</label>
    </div>
    <h2>Simple Minemap</h2>
    <div>Probe Age {{ probeAge }} </div>
    <div>Last State: {{ lastUpd }} </div>
    <div>
      Selected Probe:
      <span>host: {{ actProbe.host }} </span>
      <span>probe: {{ actProbe.probe }} </span>
      <span>age: {{ actProbe.age }}s </span>
      <span>state: {{ actProbe.state }} </span>
    </div>
    <div>
      Probe Message:<br>
      <tt>{{ actProbe.msg }} </tt>
    </div>

    <table
      id="minemap"
      border="1"
    >
      <tr
        style="line-height: 150px"
      >
        <th>host</th>
        <th
          v-for="probe in probeNames"
          :key="probe"
          class="rotate"
        >
          <div>{{ probe }}</div>
        </th>
      </tr>
      <tr
        v-for="host in hosts"
        v-if="check_array_is_null(host.grp_change)"
        :key="host.name"
      >
        <td>{{ host.name }}</td>
        <td
          v-for="probe in probeNames"
          :key="probe"
          :class="{
            err: isErrorState(host.name, probe),
            unknown: isUnknownState(host.name, probe),
            warn: isWarningState(host.name, probe)
          }"
          :title="msgStr(host.name, probe)"
          @click="setActProbe(host.name, probe)"
        >
          {{ shortMinemapStr(host.name, probe) }}
        </td>
      </tr>
      <tbody v-else>
        <tr
          v-for="(group, index) in host.grp_change"
          :key="group"
          v-if="group!=null"
          v-bind:style="{ fontSize: (1/((index+1)/1.5) + 1) + 'em' }"
          style="text-align: center;">
            <td
              v-bind:colspan="probeNames.length + 1"
            >{{ group }}</td>
        </tr>
        <tr>
          <td>{{ host.name }}</td>
          <td
            v-for="probe in probeNames"
            :key="probe"
            :class="{
              err: isErrorState(host.name, probe),
              unknown: isUnknownState(host.name, probe),
              warn: isWarningState(host.name, probe)
            }"
            :title="msgStr(host.name, probe)"
            @click="setActProbe(host.name, probe)"
          >
            {{ shortMinemapStr(host.name, probe) }}
          </td>
        </tr>
      </tbody>
    </table><br>

    <h2>hostlist</h2>
    <table id="hostlist">
      <thead>
        <tr>
          <th>host</th><th>addr</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="host in hosts"
          :key="host.name"
        >
          <td>{{ host.name }}</td><td> {{ hostcfg[host.name].addr }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import axios from 'axios'
var autorefreshInterval
var THREESECONDS = 3000
var notifyHist = {}

export default {
  name: 'Timon',
  data: function () {
    return {
      lastUpd: Date.now(),
      probeAge: 0,
      mtime: '-',
      tmp_state: {}, // temporary full timon state
      tmp_hosts: [], // temporary list of hosts
      state: {}, // full timon state
      hosts: [], // list of hosts
      probeNames: [], // ordered list of probe names
      name: 'Timon Web Interface 1',
      cfg: {}, // full timon config
      hostcfg: {}, // timon hosts config
      probemap: [], // short probename to full probename
      autoRefresh: false,
      minemap: {},
      actProbe: {
        host: '-',
        probe: '-',
        age: '-',
        state: '-',
        msg: '-'
      }
    }
  },
  watch: {
    autoRefresh: 'toggleAutoRefresh'
  },
  mounted: function () {
    console.log('mounted', this.name)
    this.refresh()
  },
  methods: {
    toggleAutoRefresh () {
      var self = this
      if (self.autoRefresh) {
        autorefreshInterval = setInterval(self.refresh, THREESECONDS)
      } else {
        clearInterval(autorefreshInterval)
      }
    },
    setActProbe (host, probename) {
      var info = this.minemapInfo(host, probename)
      var probe = this.actProbe
      probe.host = host
      probe.probe = probename
      probe.age = (this.lastUpd - info.age).toFixed(0)
      probe.state = info.state
      probe.msg = info.msg
    },
    minemapInfo (host, probename) {
      var probeName = this.minemap[host][probename]
      var probeStates
      var probeState
      var probelen
      var statestr = '#'
      var rslt = {
        age: '?',
        state: statestr,
        newError: false,
        msg: ''
      }
      if (typeof probeName === 'undefined') {
        rslt.state = '-'
        return rslt
      }
      probeStates = this.state.probe_state[probeName]
      probelen = probeStates.length
      if (probelen === 0) {
        rslt.state = '?'
        return rslt
      } else {
        probeState = probeStates[probelen - 1]
        rslt.age = probeState[0] - this.probeAge
        rslt.probe_tstamp = probeState[0]
        rslt.state = probeState[1]
        rslt.msg = probeState[2]
        if (rslt.state !== 'OK' && probeStates.length > 1) {
          if (probeStates[probelen - 2][1] === 'OK') {
            rslt.newError = true
          }
        }
      }
      return rslt
    },
    msgStr (host, probename) {
      var rslt = this.minemapInfo(host, probename);
      let message = probename + "\n" + rslt.msg;
      return message;
    },
    minemapStr (host, probename) {
      var rslt = this.minemapInfo(host, probename)
      return rslt.state
    },
    shortMinemapStr (host, probename) {
      var minemapstr = this.minemapStr(host, probename)
      return minemapstr.substring(0, 3)
    },
    isErrorState (host, probename) {
      return this.shortMinemapStr(host, probename) === 'ERR'
    },
    isWarningState (host, probename) {
      return this.shortMinemapStr(host, probename) === 'WAR'
    },
    isUnknownState (host, probename) {
      return this.shortMinemapStr(host, probename) === 'UNK'
    },
    mk_minemap_cfg (cfg) {
      var probes = this.probes = {}
      var probemap = this.probemap = {}
      var fullProbename, probename
      var minemap = this.minemap = {}
      for (let [host, hostCfg] of Object.entries(cfg.hosts)) {
        console.log('host', host, hostCfg)
        probemap[host] = {}
        minemap[host] = {}
        for (fullProbename of hostCfg.probes) {
          probename = cfg.all_probes[fullProbename]['probe']
          console.log(fullProbename, probename)
          probes[probename] = probename
          probemap[host][probename] = {
            full_name: fullProbename,
            short_name: probename
          }
          minemap[host][probename] = fullProbename
        }
      }
    },
    parse_host_group(host_group, fields=[], deepness=0){
      let end_list = [];
      for(let [entry_idx, entry] of Object.entries(host_group)){
          fields[deepness] = entry["name"];
          if(entry["entries"] !== undefined && entry["entries"].length > 0){
              if(typeof(entry["entries"][0])==="string"){
                  for(let server of entry["entries"]){
                      end_list.push({
                          "name": server,
                          "grp_change": [...fields]
                      });
                      for(let field in fields){
                          fields[field] = null;
                      }
                  }
              }
              else{
                  end_list = end_list.concat(this.parse_host_group(entry["entries"], fields, deepness+1));
              }
          }
      }
      return(end_list);
    },
    parse_cfg (cfg) {
      this.cfg = cfg
      console.log('cfg', cfg)
      this.hosts = []
      this.hostcfg = cfg.hosts
      // make host list
      if(cfg.hasOwnProperty("host_group")){
        this.hosts = this.parse_host_group(cfg.host_group)
      }
      else{
        var orderedHosts = []
        var unorderedHosts = []
        for (let [host, hostcfg] of Object.entries(cfg.hosts)) {
          console.log('host', host, hostcfg)
        if ('order_key' in hostcfg && hostcfg['order_key']) {
          orderedHosts[hostcfg['order_key']] = {"name": host, "grp_change": []}
        } else {
            unorderedHosts.push({"name": host, "grp_change": []})
          }
        }
        // remove empty array index
        orderedHosts = orderedHosts.filter(function (e) { return e })
        orderedHosts = orderedHosts.concat(unorderedHosts)
        this.hosts = orderedHosts
      }
      console.log('hosts: ', this.hosts)
      this.probeNames = cfg.active_probes
      console.log('probe names: ', this.probeNames)

      this.mk_minemap_cfg(cfg)
      return
    },
    notify (state) {
      for (let probename of Object.keys(state.probe_state)) {
        let host = probename.split('_', 1)[0]
        let realProbename = probename.slice(host.length + 1, probename.length)
        let info = this.minemapInfo(host, realProbename)
        if (info.newError) {
          if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(function (permission) {
              // If the user accepts, let's create a notification
              if (permission === 'granted') {
                if (notifyHist[realProbename] !== info.probe_tstamp) {
                  notifyHist[realProbename] = info.probe_tstamp
                  let options = {
                    requireInteraction: true
                  }
                  let _ = new Notification(
                    `host: ${host} \nprobe: ${realProbename} \nerror: ${info.msg}`,
                    options)
                }
              }
            })
          }
        }
      }
    },
    parse_state (state) {
      this.notify(state)
    },
    parse_cfg_state (cfg, state) {
      this.cfg = cfg
      this.state = state
      this.parse_cfg(cfg)
      this.parse_state(state)
      this.lastUpd = Date.now() / 1000
      this.mtime = state.mtime
      this.probeAge = this.lastUpd - state.mtime
    },
    refresh () {
      this._cfg = null
      this.tmp_state = null

      console.log('refreshing', this.name)
      axios.get('../timoncfg_state.json')
        .then(response => {
          var _cfg = this._cfg = response.data
          console.log('got cfg', _cfg)
          if (_cfg && this._state) {
            this.parse_cfg_state(_cfg, this._state)
          }
        })
        .catch(e => {
          console.log('error: ', e)
        })
      axios.get('../timon_state.json')
        .then(response => {
          var _state = this._state = response.data
          console.log('got state', _state)
          if (_state && this._cfg) {
            this.parse_cfg_state(this._cfg, _state)
          }
        })
        .catch(e => {
          console.log('error: ', e)
        })
    },
    check_array_is_null(array1){
      return array1.every(function(element) {
        return element === null; 
      });
    }
  }
}
</script>
