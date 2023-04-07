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
          :class="{
            errtxt: worst_rslt_by_probe[probe]['status'] == 'ERR' || worst_rslt_by_probe[probe]['status'] == 'TIM',
            unknowntxt: worst_rslt_by_probe[probe]['status'] == 'UNK',
            warntxt: worst_rslt_by_probe[probe]['status'] == 'WAR',
            oktxt: worst_rslt_by_probe[probe]['status'] == 'OK',
            timonerrtxt: probes_status.indexOf(worst_rslt_by_probe[probe]['status']) == -1,
          }"
          class="rotate"
        >
          <div>{{ probe }} ({{ worst_rslt_by_probe[probe]['cnt'] }})</div>
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
            err: isErrorState(host.name, probe) || isTimeoutState(host.name, probe),
            unknown: isUnknownState(host.name, probe),
            warn: isWarningState(host.name, probe),
            timonerr: isIncorrectState(host.name, probe),
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
              err: isErrorState(host.name, probe) || isTimeoutState(host.name, probe),
              unknown: isUnknownState(host.name, probe),
              warn: isWarningState(host.name, probe),
              timonerr: isIncorrectState(host.name, probe),
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
var probe_notifs_to_send = []
var PROBE_STATUS_BY_PRIORITY = ["ERR", "TIM", "WAR", "UNK", "OK"]

export default {
  name: 'Timon',
  data: function () {
    return {
      lastUpd: Date.now() / 1000,
      probeAge: 0,
      mtime: '-',
      tmp_state: {}, // temporary full timon state
      tmp_hosts: [], // temporary list of hosts
      state: {}, // full timon state
      hosts: [], // list of hosts
      probeNames: [], // ordered list of probe names
      worst_rslt_by_probe: {}, // worstrslt status and cnt by probenames
      probe_last_rslt_by_host: {}, // probe info by hostname
      name: 'Timon Web Interface 1',
      cfg: {}, // full timon config
      hostcfg: {}, // timon hosts config
      probemap: [], // short probename to full probename
      autoRefresh: false,
      probes_status: PROBE_STATUS_BY_PRIORITY,
      minemap: {},
      actProbe: {
        host: '-',
        probe: '-',
        age: '-',
        state: '-',
        msg: '-'
      },
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
      probe.interval = info.interval;
    },
    minemapInfo (host, probename) {
      var rslt = this.probe_last_rslt_by_host[host][probename]
      if (rslt == undefined){
        var statestr = '#'
        var rslt = {
          age: '?',
          state: statestr,
          newError: false,
          interval: 0,
          msg: ''
        }
        if (!(host in this.minemap) || !(probename in this.minemap[host])){
          rslt["state"] = "-";
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
      var rslt = this.minemapInfo(host, probename);
      return rslt.state
    },
    shortMinemapStr (host, probename) {
      var minemapstr = this.minemapStr(host, probename)
      return minemapstr.substring(0, 3)
    },
    isTimeoutState (host, probename) {
      return this.shortMinemapStr(host, probename) === 'TIM'
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
    isIncorrectState (host, probename) {
      var p_status = this.shortMinemapStr(host, probename)
      return p_status != "-" && PROBE_STATUS_BY_PRIORITY.indexOf(p_status) === -1
    },
    mk_minemap_cfg (cfg) {
      var probes = this.probes = {}
      var probemap = this.probemap = {}
      var fullProbename, probename
      var minemap = this.minemap = {}
      for (let [host, hostCfg] of Object.entries(cfg.hosts)) {
        probemap[host] = {}
        minemap[host] = {}
        for (fullProbename of hostCfg.probes) {
          probename = cfg.all_probes[fullProbename]['probe']
          probes[probename] = probename
          probemap[host][probename] = {
            full_name: fullProbename,
            short_name: probename
          }
          minemap[host][probename] = fullProbename
        }
      }
    },
    parse_host_group(host_group, fields=[], depth=0){
      /*
      This function parse recursively list host_group and return result what is a list of
      hosts.Each host is a dict with a name attribute (the server name) and a grp_change
      attribute what is a list of fields that change between this server and the server before
      'fields' are the list of fields in the server what we use to separate in table
      */
      let result = [];
      for(let entry of Object.values(host_group)){
          fields[depth] = entry["name"];
          if(entry["entries"] !== undefined && entry["entries"].length > 0){
              if(typeof(entry["entries"][0]) === "string"){
                  for(let server of entry["entries"]){
                      result.push({
                          "name": server,
                          "grp_change": [...fields]
                      });
                      for(let field in fields){
                          fields[field] = null;
                      }
                  }
              }
              else{
                  result = result.concat(this.parse_host_group(entry["entries"], fields, depth+1));
              }
          }
      }
      return(result);
    },
    parse_cfg (cfg) {
      /*
      Parses configuration / determines order of hosts to be displayed
      */
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
      this.worst_rslt_by_probe = Object.assign({}, ...this.probeNames.map((x) => ({[x]: {"status": "OK", "cnt": 0}})));
      this.mk_minemap_cfg(cfg)
      return
    },
    notify () {
      if (Notification.permission === 'granted' ) {
        let options = {
          requireInteraction: true
        }
        //  send notif
        if (probe_notifs_to_send.length < 5) {
          // Maximum five notifications
          for( probeinfo in probe_notifs_to_send ){
            let host = probeinfo.host
            let probename = probeinfo.probename
            let msg = probeinfo.msg
            let _ = new Notification(
              `host: ${host} \nprobe: ${probename} \nerror: ${msg}`,
              options)
            }
        }
        else{
          let host = "all"
          let probename = "all"
          let msg = `${probe_notifs_to_send.length} new errors`
          let _ = new Notification(
            `host: ${host} \nprobe: ${probename} \nerror: ${msg}`,
            options)
        }
      }
      probe_notifs_to_send = [];
    },
    parse_state (state) {
      var statestr = '#'
      for (let probename of Object.keys(state.probe_state)) {
        let host = probename.split('_', 1)[0]
        if (this.probe_last_rslt_by_host[host] == undefined){
          this.probe_last_rslt_by_host[host] = {}
        }
        let realProbename = probename.slice(host.length + 1, probename.length)
        var cur_probe_rslt = this.probe_last_rslt_by_host[host][realProbename] = {
          age: '?',
          state: statestr,
          newError: false,
          interval: 0,
          probe_tstamp: 0,
          msg: '',
          probename: realProbename,
          host: host
        }
        if (!(host in this.minemap) || !(realProbename in this.minemap[host])){
          cur_probe_rslt["state"] = "-";
          continue;
        }
        var scheduleStr = this.cfg.all_probes[probename]['schedule'];
        cur_probe_rslt["interval"] = this.cfg.schedules[scheduleStr]["interval"];
        var probeStates = this.state.probe_state[probename];
        var probelen = probeStates.length;
        if (probelen === 0) {
          cur_probe_rslt["state"] = '?';
        } else {
          var probeState = probeStates[probelen - 1];
          cur_probe_rslt["age"] = this.lastUpd - probeState[0];
          cur_probe_rslt["probe_tstamp"] = probeState[0];
          var cur_state = cur_probe_rslt["state"] = probeState[1];
          cur_probe_rslt["msg"] = probeState[2];
          if (cur_state !== 'OK' && probeStates.length > 1) {
            if (probeStates[probelen - 2][1] === 'OK') {
              cur_probe_rslt["newError"] = true;
            }
          }
          if(cur_probe_rslt["age"] > 2.5 * cur_probe_rslt["interval"]){
            cur_probe_rslt["state"] = "TIMEOUT";
          }
        }
        if(realProbename in this.worst_rslt_by_probe){
          let short_state = cur_probe_rslt["state"].substring(0, 3)
          let state_idx_prior = PROBE_STATUS_BY_PRIORITY.indexOf(short_state)
          let cur_worst_state = this.worst_rslt_by_probe[realProbename]["status"]
          let cur_worst_idx_prior = PROBE_STATUS_BY_PRIORITY.indexOf(cur_worst_state)
          if(state_idx_prior < cur_worst_idx_prior){
            this.worst_rslt_by_probe[realProbename]["status"] = short_state;
            this.worst_rslt_by_probe[realProbename]["cnt"] = 1;
          }
          else if(state_idx_prior === cur_worst_idx_prior){
            this.worst_rslt_by_probe[realProbename]["cnt"] ++;
          }
        }
        if(cur_probe_rslt["newError"]){
          probe_notifs_to_send.push(cur_probe_rslt);
        }
      }
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
          // console.log('got cfg', _cfg)
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
            console.log(probe_notifs_to_send.length)
            if(probe_notifs_to_send.length > 0){
              this.notify();
            }
          }
        })
        .catch(e => {
          console.log('error: ', e)
        })
    },
    check_array_is_null(array1){
      /* Check if all elements in array1 are null */
      return array1.every(function(element) {
        return element === null;
      });
    }
  }
}

if (Notification.permission === "default"){
  Notification.requestPermission()
}
</script>
